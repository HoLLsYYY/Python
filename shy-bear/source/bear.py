import os, sys, json, math, random, time, threading, uuid
from pathlib import Path
import requests
import hashlib, winreg
from urllib.parse import urlencode
from windows_http import request as windows_request
from bouquet_timeline import BouquetAnimation,DURATION as BOUQUET_DURATION
from updater import Updater,VERSION
from PySide6.QtCore import Qt,QTimer,QObject,Signal,QRectF,QPointF
from PySide6.QtGui import QPixmap,QImage,QPainter,QColor,QFont,QFontDatabase,QIcon,QAction,QFontMetrics
from PySide6.QtWidgets import QApplication,QWidget,QVBoxLayout,QLabel,QPushButton,QLineEdit,QComboBox,QCheckBox,QSystemTrayIcon,QMenu,QMessageBox
from protocol import new_code,key_for,topic_for,encode,decode

BASE=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent.parent))
ASSETS=BASE/'assets'
CONFIG=Path(os.environ.get('LOCALAPPDATA',str(Path.home()))) / 'ShyBear' / 'config.json'
RELAY='https://ntfy.sh/'
SHY_DURATION=5.5
SHY_SWINGS=5
ACTION_START=6.2
EXIT_DURATION=7.0

class Network(QObject):
    received=Signal(dict)
    status=Signal(str)
    sent=Signal(str)
    diagnostics=Signal(str)
    def __init__(self):
        super().__init__();self.generation=0;self.code=None;self.outgoing_code=None;self.seen=set();self.use_windows=os.name=='nt';self.device_id=uuid.uuid4().hex
    def connect_code(self,code):
        key_for(code);self.code=code;self.generation+=1
        threading.Thread(target=self.listen,args=(code,self.generation),daemon=True).start()
    def connect_pair(self,own_code,partner_code=None):
        if partner_code:key_for(partner_code)
        self.outgoing_code=partner_code
        self.connect_code(own_code)
    @staticmethod
    def error_reason(error):
        if isinstance(error,requests.exceptions.SSLError):return 'ошибка сертификата HTTPS'
        if isinstance(error,requests.exceptions.ProxyError):return 'ошибка прокси'
        if isinstance(error,requests.exceptions.Timeout):return 'сервер не ответил вовремя'
        if isinstance(error,requests.exceptions.HTTPError):
            code=error.response.status_code if error.response is not None else '?'
            return f'сервер вернул HTTP {code}'
        if isinstance(error,requests.exceptions.ConnectionError):return 'не удаётся соединиться с ntfy.sh'
        if isinstance(error,OSError) and getattr(error,'winerror',None):
            return f'системное подключение Windows: ошибка {error.winerror}'
        return 'неверный ответ сервера'
    def listen(self,code,generation):
        delay=2;poll=self.use_windows;cursor='60s';connected=False
        def receive(line):
            nonlocal cursor
            event=json.loads(line)
            if event.get('event')!='message':return
            cursor=event.get('id',cursor)
            try:data=decode(code,event['message'],self.seen)
            except (ValueError,KeyError,TypeError):return
            except Exception:return
            if data.get('sender')==self.device_id:return
            if data.get('target') and data['target']!=self.device_id:return
            self.received.emit(data)
        while generation==self.generation:
            try:
                params={'since':cursor}
                if poll:params['poll']='1'
                if poll and self.use_windows:
                    body=self.system_request('GET',RELAY+topic_for(code)+'/json?'+urlencode(params))
                    if not connected:self.status.emit('Связь подключена через Windows')
                    connected=True;delay=2
                    for line in body.splitlines():
                        if generation!=self.generation:return
                        if line:receive(line)
                else:
                    with requests.get(RELAY+topic_for(code)+'/json',params=params,stream=True,timeout=(10,15 if poll else 70)) as r:
                        r.raise_for_status()
                        if not connected:self.status.emit('Связь подключена (резервный режим)' if poll else 'Связь подключена')
                        connected=True;delay=2
                        for line in r.iter_lines(chunk_size=1):
                            if generation!=self.generation:return
                            if line:receive(line)
                if poll:
                    for _ in range(50):
                        if generation!=self.generation:return
                        time.sleep(.1)
            except Exception as error:
                if generation!=self.generation:return
                connected=False;poll=True
                self.use_windows=os.name=='nt'
                self.status.emit(f'Нет связи: {self.error_reason(error)}. Повтор через {delay} с')
                for _ in range(delay*10):
                    if generation!=self.generation:return
                    time.sleep(.1)
                delay=min(30,delay*2)
    @staticmethod
    def system_request(method,url,payload=None):
        status,body=windows_request(method,url,payload)
        if status>=400:
            response=requests.Response();response.status_code=status
            raise requests.HTTPError(f'HTTP {status}',response=response)
        return body
    def diagnose(self):
        def run():
            lines=['Мишка: проверка связи',time.strftime('%Y-%m-%d %H:%M:%S')]
            def check(label,fn):
                try:lines.append(label+': '+fn())
                except Exception as error:
                    detail=self.error_reason(error)+' ['+type(error).__name__+']'
                    queue=[error];visited=set();codes=[]
                    while queue:
                        current=queue.pop()
                        if id(current) in visited:continue
                        visited.add(id(current))
                        for attr in ('winerror','errno'):
                            code=getattr(current,attr,None)
                            if isinstance(code,int) and code not in codes:codes.append(code)
                        for child in [getattr(current,'reason',None),getattr(current,'__cause__',None),getattr(current,'__context__',None),*getattr(current,'args',())]:
                            if isinstance(child,BaseException):queue.append(child)
                    if codes:detail+='; коды '+','.join(map(str,codes))
                    lines.append(label+': '+detail)
            def ordinary():
                response=requests.get(RELAY+'v1/health',timeout=(8,10));response.raise_for_status()
                return f'HTTP {response.status_code}'
            check('Обычный HTTPS',ordinary)
            check('Системный HTTPS Windows',lambda:'OK' if b'healthy' in self.system_request('GET',RELAY+'v1/health') else 'неожиданный ответ')
            code=self.code or new_code()
            check('Подписка через Windows',lambda:'OK' if self.system_request('GET',RELAY+topic_for(code)+'/json?poll=1&since=1s') is not None else 'нет ответа')
            report='\n'.join(lines)
            try:
                CONFIG.parent.mkdir(parents=True,exist_ok=True)
                path=CONFIG.parent/'connection-report.txt';path.write_text(report,encoding='utf-8')
                report+='\n\nОтчёт: '+str(path)
            except OSError:pass
            self.diagnostics.emit(report)
        threading.Thread(target=run,daemon=True).start()
    def send(self,command,ref=None,target=None,channel=None):
        code=channel or self.outgoing_code or self.code
        if not code:return
        payload,ident=encode(code,command,ref,sender=self.device_id,target=target,reply_to=self.code)
        def run():
            try:
                if self.use_windows:self.system_request('POST',RELAY+topic_for(code),payload)
                else:
                    try:
                        r=requests.post(RELAY+topic_for(code),data=payload,headers={'Content-Type':'text/plain'},timeout=15)
                        r.raise_for_status()
                    except requests.RequestException:
                        if os.name!='nt':raise
                        self.system_request('POST',RELAY+topic_for(code),payload)
                        self.use_windows=True
                if command!='ack':self.sent.emit(ident)
            except Exception as error:
                self.status.emit(f'Не удалось отправить: {self.error_reason(error)}')
        threading.Thread(target=run,daemon=True).start()

def ease(t):
    t=max(0,min(1,t));return t*t*(3-2*t)

class Pet(QWidget):
    def __init__(self,control):
        super().__init__(None,Qt.FramelessWindowHint|Qt.WindowStaysOnTopHint|Qt.Tool|Qt.WindowDoesNotAcceptFocus)
        self.control=control;self.setAttribute(Qt.WA_TranslucentBackground);self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFixedSize(300,265)
        self.images={name:QPixmap(str(ASSETS/(name+'.png'))) for name in ['peek']+[f'{s}{i}' for s in ['heart','shy'] for i in range(4)]}
        self.motion_meta=json.loads((ASSETS/'motion.json').read_text(encoding='utf-8'))
        self.motion={name:QPixmap(str(ASSETS/f'{name}-motion.png')) for name in self.motion_meta}
        self.bouquet=BouquetAnimation(ASSETS,self.motion,self.motion_meta)
        self.active=False;self.action='shy';self.started=0;self.side='right'
        self.timer=QTimer(self);self.timer.setTimerType(Qt.PreciseTimer);self.timer.setSingleShot(True);self.timer.timeout.connect(self.tick);self.next_frame=0
        self.rare=QTimer(self);self.rare.setSingleShot(True);self.rare.timeout.connect(self.random_visit);self.schedule()
    def schedule(self):self.rare.start(random.randint(15*60000,30*60000))
    def random_visit(self):
        if self.control.auto.isChecked() and not self.active:self.play(random.choice(['heart','shy','bouquet']))
        self.schedule()
    def play(self,action):
        self.action='shy' if action=='show' else action;self.started=time.monotonic();self.active=True
        self.side=random.choice(['left','right'])
        self.next_frame=self.started;self.timer.start(0)
        screen=QApplication.primaryScreen();g=screen.geometry();a=screen.availableGeometry()
        self.setWindowFlag(Qt.WindowTransparentForInput,self.action=='bouquet')
        if self.action=='bouquet':
            self.setFixedSize(g.width(),a.bottom()-g.top()+1);self.move(g.left(),g.top())
        else:
            self.setFixedSize(300,265)
            self.move(g.left() if self.side=='left' else g.right()-self.width()+1,a.bottom()-self.height()+1)
        self.show();self.raise_();self.update()
    def vanish(self):self.active=False;self.timer.stop();self.hide()
    def tick(self):
        if not self.active:return
        now=time.monotonic()
        if now-self.started>=(BOUQUET_DURATION if self.action=='bouquet' else self.action_end()+EXIT_DURATION):self.vanish();return
        self.update()
        if self.next_frame<now-.1:self.next_frame=now
        self.next_frame+=1/60
        self.timer.start(max(1,round((self.next_frame-time.monotonic())*1000)))
    def action_end(self):
        return ACTION_START+(SHY_DURATION if self.action=='shy' else 7.1)
    def draw_shy(self,p,elapsed):
        self.draw_motion(p,'shy',max(0,min(1,elapsed/SHY_DURATION)),60)
    def draw_motion(self,p,name,phase,x):
        meta=self.motion_meta[name];index=min(meta['count']-1,int(max(0,min(1,phase))*meta['count']))
        w,h=meta['width'],meta['height']
        p.save()
        if self.side=='left' and name.startswith('heart'):
            # This front-facing pose contains lettering: mirror its position, not its text.
            x=self.width()-x-w
        elif self.side=='left':p.translate(self.width(),0);p.scale(-1,1)
        p.drawPixmap(QRectF(x,70,w,h),self.motion[name],QRectF(0,index*h,w,h))
        p.restore()
    def draw_entry(self,p,t):
        if t<1.1:self.draw_motion(p,'grip',0,300-100*ease(t/1.1))
        elif t<2.9:self.draw_motion(p,'grip',(t-1.1)/1.8,200)
        elif t<3.4:self.draw_motion(p,'grip',1,200)
        elif t<4:self.draw_motion(p,'release',(t-3.4)/.6,200)
        else:
            x=200-140*ease((t-4)/2.2)
            self.draw_motion(p,'walk',(t-4)/2.2,x)
    def draw_exit(self,p,t):
        if t<.4:self.draw_motion(p,'turn-right',t/.4,60)
        elif t<2.6:
            phase=(t-.4)/2.2
            self.draw_motion(p,'return-walk',phase,60+140*ease(phase))
        elif t<3:self.draw_motion(p,'turn-right',1-(t-2.6)/.4,200)
        else:self.draw_entry(p,max(0,4-(t-3)))
    def draw_heart(self,p,elapsed):
        if elapsed<.5:self.draw_motion(p,'heart-in',elapsed/.5,60)
        elif elapsed<6.6:self.draw_motion(p,'heart',((elapsed-.5)/2.4)%1,60)
        else:self.draw_motion(p,'heart-out',(elapsed-6.6)/.5,60)
    def paintEvent(self,event):
        if not self.active:return
        t=time.monotonic()-self.started;p=QPainter(self);p.setRenderHint(QPainter.Antialiasing);p.setRenderHint(QPainter.SmoothPixmapTransform)
        if self.action=='bouquet':
            self.bouquet.paint(p,t,self.width(),self.height(),.36 if self.side=='left' else .64);return
        if t<ACTION_START:self.draw_entry(p,t)
        elif t<self.action_end():
            if self.action=='shy':self.draw_shy(p,t-ACTION_START)
            else:self.draw_heart(p,t-ACTION_START)
            if self.action=='shy':
                elapsed=t-ACTION_START;p.setOpacity(min(ease(elapsed/.15),ease((SHY_DURATION-elapsed)/.15)))
                p.setPen(Qt.NoPen);p.setBrush(QColor('#fff4f8'));p.drawRoundedRect(QRectF(38 if self.side=='left' else 76,22,186,42),10,10)
                p.setPen(QColor('#653541'));p.setFont(self.control.pixel_font)
                text='я скучаю';text_width=QFontMetrics(self.control.pixel_font).horizontalAdvance(text)
                group_width=text_width+8+14;left=(38 if self.side=='left' else 76)+(186-group_width)/2
                p.drawText(QRectF(left,22,text_width,42),Qt.AlignCenter,text)
                p.setPen(Qt.NoPen);p.setBrush(QColor('#df7898'))
                heart=['0110110','1111111','1111111','0111110','0011100','0001000']
                for row,line in enumerate(heart):
                    for col,pixel in enumerate(line):
                        if pixel=='1':p.drawRect(QRectF(round(left+text_width+8)+col*2,43+row*2,2,2))
        else:
            self.draw_exit(p,t-self.action_end())
    def contextMenuEvent(self,event):
        self.control.menu.exec(event.globalPos())
    def mouseDoubleClickEvent(self,event):self.control.show();self.control.raise_()

class Control(QWidget):
    def __init__(self):
        super().__init__();self.setWindowTitle('Мишка · два компьютера');self.resize(480,650)
        self.setStyleSheet('QWidget {background:#fff8fa;color:#51343d;font-size:14px;} QPushButton {background:#f7ccda;border:0;border-radius:8px;padding:11px;} QPushButton:hover {background:#efb5c8;} QLineEdit,QComboBox {background:white;padding:8px;border:1px solid #e5c5d0;border-radius:6px;}')
        fid=QFontDatabase.addApplicationFont(str(ASSETS/'Mojangles.ttf'))
        families=QFontDatabase.applicationFontFamilies(fid);self.pixel_font=QFont(families[0] if families else 'Consolas',17)
        self.net=Network();self.net.received.connect(self.receive)
        layout=QVBoxLayout(self);title=QLabel('Твой застенчивый мишка');title.setStyleSheet('font-size:23px;font-weight:bold');layout.addWidget(title)
        self.cfg={}
        try:self.cfg=json.loads(CONFIG.read_text(encoding='utf-8'))
        except (OSError,ValueError):pass
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,r'SOFTWARE\Microsoft\Cryptography') as machine_key:
            machine_guid=winreg.QueryValueEx(machine_key,'MachineGuid')[0]
        self.machine_id=hashlib.sha256(machine_guid.encode()).hexdigest()
        same_pc=self.cfg.get('machine_id',self.machine_id)==self.machine_id
        self.own_code=self.cfg.get('own_key') if same_pc else None
        try:key_for(self.own_code or '')
        except (ValueError,TypeError):self.own_code=new_code()
        self.net.device_id=(self.cfg.get('device_id') if same_pc else None) or self.net.device_id
        layout.addWidget(QLabel('Ключ этого ПК — постоянный. Передай его партнёру:'))
        own=QLineEdit(self.own_code);own.setReadOnly(True);layout.addWidget(own)
        copy=QPushButton('Скопировать ключ этого ПК');copy.clicked.connect(lambda:QApplication.clipboard().setText(self.own_code));layout.addWidget(copy)
        layout.addWidget(QLabel('Ключ ПК партнёра — анимации будут отправляться ему:'))
        self.code=QLineEdit();self.code.setPlaceholderText('Вставь ключ партнёра BEAR1-…');self.code.setEchoMode(QLineEdit.Password);layout.addWidget(self.code)
        self.code.setText(self.cfg.get('partner_key',self.cfg.get('code','')))
        connect=QPushButton('Подключить партнёра');connect.clicked.connect(self.connect);layout.addWidget(connect)
        diagnostics=QPushButton('Проверить связь');diagnostics.clicked.connect(self.net.diagnose);layout.addWidget(diagnostics)
        self.net.diagnostics.connect(lambda report:QMessageBox.information(self,'Проверка связи',report))
        self.auto=QCheckBox('Редко появляться самостоятельно (15–30 минут)');self.auto.setChecked(True);layout.addWidget(self.auto)
        self.startup=QCheckBox('Запускать вместе с Windows');self.startup.setChecked(self.cfg.get('autostart',True));layout.addWidget(self.startup)
        self.startup.toggled.connect(self.change_autostart)
        self.updates=QCheckBox('Автоматически скачивать и устанавливать обновления');self.updates.setChecked(self.cfg.get('updates',True));layout.addWidget(self.updates)
        self.updates.toggled.connect(lambda _:self.save())
        self.update_status=QLabel('Версия '+VERSION);self.update_status.setWordWrap(True);layout.addWidget(self.update_status)
        self.check_updates=QPushButton('Проверить обновления');layout.addWidget(self.check_updates)
        for label,cmd in [('Отправить букет','bouquet'),('Отправить сердечко','heart'),('Отправить «я скучаю»','shy'),('Попросить выглянуть','show'),('Скрыть мишку у партнёра','hide')]:
            b=QPushButton(label);b.clicked.connect(lambda checked=False,c=cmd:self.command(c));layout.addWidget(b)
        self.status=QLabel('Локальные анимации доступны без интернета');self.status.setWordWrap(True);layout.addWidget(self.status)
        self.net.status.connect(self.status.setText);self.net.sent.connect(self.sent)
        self.pet=Pet(self);self.menu=QMenu()
        for label,fn in [('Показать панель',self.open),('Сердечко',lambda:self.pet.play('heart')),('Я скучаю',lambda:self.pet.play('shy')),('Букет',lambda:self.pet.play('bouquet')),('Скрыть мишку',self.pet.vanish),('Закрыть приложение',QApplication.quit)]:
            self.menu.addAction(label,fn)
        self.tray=QSystemTrayIcon(QIcon(str(ASSETS/'heart0.png')),self);self.tray.setToolTip('Мишка — двойной щелчок открывает панель');self.tray.setContextMenu(self.menu);self.tray.activated.connect(lambda reason:self.open() if reason==QSystemTrayIcon.DoubleClick else None);self.tray.show()
        self.pending={};self.acked=set()
        self.auto.setChecked(self.cfg.get('auto',True));self.auto.toggled.connect(lambda _:self.save())
        self.save()
        partner=self.code.text().strip() or None
        try:
            if partner:
                key_for(partner)
                if partner==self.own_code:raise ValueError('В поле партнёра указан ключ этого ПК')
        except (ValueError,TypeError):
            partner=None;self.status.setText('Ключ партнёра неполный или неверный. Приём команд доступен.')
        self.net.connect_pair(self.own_code,partner)
    def open(self):self.show();self.raise_();self.activateWindow()
    def connect(self):
        partner=self.code.text().strip()
        if partner==self.own_code:
            QMessageBox.warning(self,'Ключ партнёра','Это ключ этого ПК. Вставь ключ другого компьютера.');return
        try:self.net.connect_pair(self.own_code,partner or None)
        except Exception as e:QMessageBox.warning(self,'Ключ партнёра',str(e));return
        self.save();self.status.setText('Подключаюсь…')
    def change_autostart(self,enabled):
        self.save()
        if getattr(sys,'frozen',False):self.apply_autostart(enabled)
    def apply_autostart(self,enabled):
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER,r'Software\Microsoft\Windows\CurrentVersion\Run') as key:
                if enabled:winreg.SetValueEx(key,'ShyBear',0,winreg.REG_SZ,'"'+sys.executable+'" --background')
                else:
                    try:winreg.DeleteValue(key,'ShyBear')
                    except FileNotFoundError:pass
        except OSError as error:QMessageBox.warning(self,'Автозапуск',str(error))
    def save(self):
        CONFIG.parent.mkdir(parents=True,exist_ok=True)
        temporary=CONFIG.with_name(CONFIG.name+'.tmp')
        temporary.write_text(json.dumps({'own_key':self.own_code,'partner_key':self.code.text().strip(),'machine_id':self.machine_id,'device_id':self.net.device_id,'auto':self.auto.isChecked(),'autostart':self.startup.isChecked(),'updates':self.updates.isChecked()}),encoding='utf-8')
        temporary.replace(CONFIG)
    def command(self,cmd):
        if self.net.outgoing_code:
            self.status.setText('Отправляю…');self.net.send(cmd)
        else:self.status.setText('Вставь ключ ПК партнёра и нажми «Подключить партнёра»')
    def play_local(self,cmd):
        if cmd=='hide':self.pet.vanish()
        else:self.pet.play(cmd)
    def sent(self,ident):
        if ident in self.acked:return
        self.pending[ident]=True;self.status.setText('Отправлено, жду подтверждение от мишки…')
        QTimer.singleShot(12000,lambda:self.timeout(ident))
    def timeout(self,ident):
        if self.pending.pop(ident,None):self.status.setText('Подтверждение не пришло: проверьте ПК с мишкой и код')
    def receive(self,data):
        if data['cmd']=='ack':
            self.acked.add(data.get('ref'))
            self.pending.pop(data.get('ref'),None);self.status.setText('Мишка получил команду ✓')
        else:
            self.play_local(data['cmd'])
            reply=data.get('reply_to')
            if reply:
                try:key_for(reply)
                except (ValueError,TypeError):return
            self.net.send('ack',data['id'],target=data.get('sender'),channel=reply)
    def closeEvent(self,event):
        self.save()
        if QSystemTrayIcon.isSystemTrayAvailable():event.ignore();self.hide();self.tray.showMessage('Мишка','Работает в трее. Выход — через меню значка.',QSystemTrayIcon.Information,2500)
        else:QApplication.quit()

def main():
    if '--self-test' in sys.argv or '--network-test' in sys.argv:os.environ['QT_QPA_PLATFORM']='offscreen'
    app=QApplication(sys.argv);app.setQuitOnLastWindowClosed(False)
    if '--network-test' in sys.argv:
        network=Network();report=Path(sys.argv[sys.argv.index('--network-test')+1])
        def finished(text):
            report.write_text(text,encoding='utf-8');app.quit()
        network.diagnostics.connect(finished);network.diagnose()
        app.exec();return
    if '--self-test' in sys.argv:
        global CONFIG
        CONFIG=Path(sys.argv[sys.argv.index('--self-test')+1]).with_suffix('.config.json')
        window=Control()
        assert all(not image.isNull() for image in window.pet.images.values())
        assert all(not image.isNull() for image in window.pet.motion.values())
        assert window.pixel_font.family()!='Consolas'
        assert not window.pet.bouquet.flowers.isNull()
        window.pet.play('shy');window.pet.started=time.monotonic()-6;app.processEvents()
        assert not window.pet.grab().isNull()
        payload,_=encode(new_code(),'heart')
        report=Path(sys.argv[sys.argv.index('--self-test')+1])
        report.write_text(json.dumps({'ok':True,'assets':len(window.pet.images),'font':window.pixel_font.family(),'frozen':bool(getattr(sys,'frozen',False))}),encoding='utf-8')
        return
    from PySide6.QtNetwork import QLocalServer,QLocalSocket
    socket=QLocalSocket();socket.connectToServer('ShyBear.desktop.v1')
    if socket.waitForConnected(300):return
    server=QLocalServer();server.listen('ShyBear.desktop.v1')
    window=Control()
    if getattr(sys,'frozen',False):window.apply_autostart(window.startup.isChecked())
    window.updater=Updater(window,CONFIG);window.updater.status.connect(window.update_status.setText)
    window.check_updates.clicked.connect(lambda:window.updater.check(manual=True))
    if '--update-token' in sys.argv:
        marker=Path(sys.argv[sys.argv.index('--update-token')+1])
        if marker.resolve()==(CONFIG.parent/'updates/boot-ok.txt').resolve():
            QTimer.singleShot(2000,lambda:marker.write_text(VERSION,encoding='utf-8'))
    if '--background' not in sys.argv:window.show()
    def reopen():
        peer=server.nextPendingConnection()
        if peer:peer.disconnectFromServer();peer.deleteLater()
        window.open()
    server.newConnection.connect(reopen)
    if '--demo' in sys.argv:QTimer.singleShot(1000,lambda:window.pet.play('shy'))
    sys.exit(app.exec())

if __name__=='__main__':main()


