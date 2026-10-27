"""Background updates from this app's public GitHub releases; no account token on clients."""
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
from pathlib import Path
from urllib.parse import urlsplit
from PySide6.QtCore import QObject, Signal, QTimer
from windows_http import request

VERSION='5.3.1'
REPOSITORY='HoLLsYYY/Python'
RELEASES_URL=f'https://api.github.com/repos/{REPOSITORY}/releases?per_page=30'
MAX_EXE_BYTES=200*1024*1024

def version_tuple(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d+\.\d+\.\d+',value):
        raise ValueError('Неверная версия')
    return tuple(map(int,value.split('.')))

def select_release(releases,current=VERSION):
    candidates=[]
    for release in releases:
        tag=release.get('tag_name','')
        if release.get('draft') or release.get('prerelease') or not tag.startswith('bear-v'):continue
        try:version=version_tuple(tag[6:])
        except ValueError:continue
        if version<=version_tuple(current):continue
        assets=[a for a in release.get('assets',[]) if a.get('name')=='Bear.exe' and a.get('state')=='uploaded']
        if len(assets)!=1:continue
        asset=assets[0];parts=urlsplit(asset.get('browser_download_url',''))
        expected=f'/{REPOSITORY}/releases/download/{tag}/Bear.exe'
        digest=asset.get('digest','')
        if (parts.scheme!='https' or parts.netloc!='github.com' or parts.path!=expected
            or parts.query or parts.fragment or not re.fullmatch(r'sha256:[a-fA-F0-9]{64}',digest)
            or not isinstance(asset.get('size'),int) or not 0<asset['size']<=MAX_EXE_BYTES):continue
        candidates.append((version,{'version':tag[6:],'url':asset['browser_download_url'],
                                    'sha256':digest[7:].lower(),'size':asset['size']}))
    return max(candidates,key=lambda item:item[0])[1] if candidates else None

def verify_candidate(path,release):
    if path.stat().st_size!=release['size']:raise ValueError('Неполная загрузка обновления')
    with path.open('rb') as source:
        if source.read(2)!=b'MZ':raise ValueError('Обновление не является приложением Windows')
        source.seek(0);digest=hashlib.file_digest(source,'sha256').hexdigest()
    if digest!=release['sha256']:raise ValueError('Контрольная сумма обновления не совпала')

def smoke_test(path,folder):
    report=folder/'candidate-smoke.json'
    report.unlink(missing_ok=True)
    result=subprocess.run([str(path),'--self-test',str(report)],timeout=60,
                          creationflags=subprocess.CREATE_NO_WINDOW,env=child_environment())
    if result.returncode or not report.exists() or not json.loads(report.read_text(encoding='utf-8')).get('ok'):
        raise RuntimeError('Новая версия не прошла проверку запуска')

def child_environment():
    # A second PyInstaller EXE must unpack its own runtime, not reuse the running one's.
    environment=os.environ.copy();environment['PYINSTALLER_RESET_ENVIRONMENT']='1'
    return environment

class Updater(QObject):
    status=Signal(str)
    ready=Signal(dict)
    finished=Signal()
    def __init__(self,control,config):
        super().__init__(control);self.control=control;self.folder=config.parent/'updates'
        self.busy=False;self.pending=None;self.manual=False
        self.ready.connect(self.prepared);self.finished.connect(self.completed)
        self.timer=QTimer(self);self.timer.timeout.connect(self.periodic);self.timer.start(60*60*1000)
        self.install_timer=QTimer(self);self.install_timer.timeout.connect(self.try_install);self.install_timer.start(1000)
        QTimer.singleShot(45000,self.periodic)
    def periodic(self):
        if self.control.updates.isChecked():self.check()
    def check(self,manual=False):
        if self.busy or self.pending:return
        if not getattr(sys,'frozen',False):
            self.status.emit('Автообновление доступно в установленной версии');return
        self.manual=manual;self.busy=True
        self.status.emit('Проверяю обновления…')
        threading.Thread(target=self.download,daemon=True).start()
    def completed(self):self.busy=False
    def download(self):
        candidate=None
        try:
            status,data=request('GET',RELEASES_URL)
            if status!=200:raise RuntimeError(f'GitHub: HTTP {status}')
            releases=json.loads(data)
            if not isinstance(releases,list):raise ValueError('Неверный ответ GitHub')
            release=select_release(releases)
            if release is None:self.status.emit(f'Версия {VERSION} актуальна');return
            self.folder.mkdir(parents=True,exist_ok=True)
            candidate=self.folder/f"Bear-{release['version']}.exe"
            self.status.emit(f"Скачиваю обновление {release['version']}…")
            status,_=request('GET',release['url'],destination=candidate,max_bytes=MAX_EXE_BYTES,timeout_ms=60000)
            if status!=200:raise RuntimeError(f'Загрузка: HTTP {status}')
            verify_candidate(candidate,release);smoke_test(candidate,self.folder)
            self.ready.emit(dict(release,candidate=str(candidate)))
        except Exception as error:
            if candidate:candidate.unlink(missing_ok=True)
            self.status.emit('Обновление отложено: '+str(error))
        finally:self.finished.emit()
    def prepared(self,release):
        self.pending=release;self.status.emit('Обновление готово. Дождусь окончания анимации и закрытия писем…')
    def try_install(self):
        if not self.pending or self.control.pet.active:return
        if (getattr(self.control,'letter_cards',[]) or getattr(self.control,'letter_composer',None) is not None
            or getattr(self.control,'letter_draft','') or getattr(self.control,'pending',{}) or getattr(self.control,'pending_kinds',{})):return
        if not self.manual and not self.control.updates.isChecked():return
        try:
            self.control.save()
            launch_installer(self.pending,self.folder)
        except Exception as error:
            self.pending=None;self.status.emit('Не удалось установить обновление: '+str(error));return
        from PySide6.QtWidgets import QApplication
        QApplication.quit()

def launch_installer(release,folder):
    target=Path(sys.executable).resolve();candidate=Path(release['candidate']).resolve()
    verify_candidate(candidate,release)
    state={'pid':os.getpid(),'target':str(target),'candidate':str(candidate),
           'sha256':release['sha256'],'marker':str(folder/'boot-ok.txt')}
    Path(state['marker']).unlink(missing_ok=True)
    state_path=folder/'install.json';state_path.write_text(json.dumps(state),encoding='utf-8')
    helper=folder/'install.ps1';helper.write_text(INSTALL_SCRIPT,encoding='utf-8-sig')
    powershell=Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
    subprocess.Popen([str(powershell),'-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass',
                      '-File',str(helper),'-StateFile',str(state_path)],
                     creationflags=subprocess.CREATE_NO_WINDOW,env=child_environment())

INSTALL_SCRIPT=r'''param([Parameter(Mandatory=$true)][string]$StateFile)
$ErrorActionPreference='Stop'
$state=Get-Content -LiteralPath $StateFile -Raw -Encoding UTF8 | ConvertFrom-Json
$backup=$state.target+'.previous'
$incoming=$state.target+'.new'
$replaced=$false
$launched=$null
try {
    $stream=[IO.File]::OpenRead($state.candidate)
    $sha=[Security.Cryptography.SHA256]::Create()
    try { $actual=[BitConverter]::ToString($sha.ComputeHash($stream)).Replace('-','').ToLower() }
    finally { $stream.Dispose(); $sha.Dispose() }
    if ($actual -ne $state.sha256) { throw 'Checksum mismatch' }
    Wait-Process -Id $state.pid -Timeout 60 -ErrorAction SilentlyContinue
    if (Get-Process -Id $state.pid -ErrorAction SilentlyContinue) { throw 'Application is still running' }
    Copy-Item -LiteralPath $state.target -Destination $backup -Force
    Copy-Item -LiteralPath $state.candidate -Destination $incoming -Force
    for ($attempt=0; $attempt -lt 30; $attempt++) {
        try { Move-Item -LiteralPath $incoming -Destination $state.target -Force; $replaced=$true; break }
        catch { if ($attempt -eq 29) { throw }; Start-Sleep -Seconds 1 }
    }
    $env:PYINSTALLER_RESET_ENVIRONMENT='1'
    $launchArgs=@('--background','--update-token',('"'+$state.marker+'"'))
    $launched=Start-Process -FilePath $state.target -ArgumentList $launchArgs -PassThru -WindowStyle Hidden
    for ($attempt=0; $attempt -lt 60; $attempt++) {
        if (Test-Path -LiteralPath $state.marker) { break }
        Start-Sleep -Seconds 1
    }
    if (!(Test-Path -LiteralPath $state.marker)) { throw 'Updated application did not start' }
    'OK' | Set-Content -LiteralPath (Join-Path (Split-Path $StateFile) 'last-update.txt')
} catch {
    $_.ToString() | Set-Content -LiteralPath (Join-Path (Split-Path $StateFile) 'last-update.txt')
    if ($replaced) {
        if ($launched -and (Get-Process -Id $launched.Id -ErrorAction SilentlyContinue)) {
            & "$env:SystemRoot\System32\taskkill.exe" /PID $launched.Id /T /F 2>$null | Out-Null
        }
        Copy-Item -LiteralPath $backup -Destination $state.target -Force
    }
    Start-Process -FilePath $state.target -ArgumentList '--background' -WindowStyle Hidden
}
'''



