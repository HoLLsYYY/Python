import os,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
os.environ['QT_QPA_PLATFORM']='offscreen';sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'source'))
import bear
from PySide6.QtWidgets import QApplication
from letter_scene import HANDOFF_TIME
app=QApplication.instance() or QApplication([])
class LetterRoutingTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.old= bear.CONFIG;bear.CONFIG=Path(self.tmp.name)/'config.json'
  with patch.object(bear.Network,'connect_pair'):self.control=bear.Control()
  self.control.letter_queue_timer.stop();self.control.net.send=Mock();self.control.present_letter=Mock()
 def tearDown(self):
  c=self.control;c.pet.vanish();c.pet.timer.stop();c.pet.rare.stop();c.tray.hide();c.deleteLater();app.processEvents();bear.CONFIG=self.old;self.tmp.cleanup()
 def test_received_letters_queue_and_handoff_exactly_once(self):
  c=self.control;reply=bear.new_code()
  for index,text in enumerate(['Первое письмо ♥','Второе письмо']):
   c.receive({'cmd':'letter','text':text,'id':str(index),'sender':'partner','reply_to':reply})
  self.assertEqual(c.pet.letter_text,'Первое письмо ♥');self.assertEqual(c.incoming_letters,['Второе письмо'])
  self.assertEqual(c.net.send.call_count,2);c.net.send.assert_called_with('ack','1',target='partner',channel=reply)
  c.pet.started-=bear.ACTION_START+HANDOFF_TIME+.1;c.pet.tick();c.pet.timer.stop();c.pet.tick();c.pet.timer.stop()
  c.present_letter.assert_called_once();self.assertEqual(c.present_letter.call_args.args[0],'Первое письмо ♥')
  c.pet.vanish();c.next_letter();self.assertEqual(c.pet.letter_text,'Второе письмо');self.assertEqual(c.incoming_letters,[])
 def test_interruption_does_not_drop_the_note(self):
  c=self.control;c.queue_letter('Сохранённое письмо');c.pet.play('heart');c.present_letter.assert_called_once();self.assertEqual(c.present_letter.call_args.args[0],'Сохранённое письмо')
 def test_send_letter_sends_text_without_local_preview(self):
  c=self.control;c.net.outgoing_code=bear.new_code();c.net.send.return_value='test-id';c.pet.play_letter=Mock()
  self.assertTrue(c.send_letter('Привет ♥'));c.net.send.assert_called_once_with('letter',text='Привет ♥');c.pet.play_letter.assert_not_called()
  c.receive({'cmd':'ack','id':'ack-id','ref':'test-id'});self.assertIn('Письмо доставлено',c.status.text())
  self.assertEqual(c.letter_draft,'')
 def test_failed_send_keeps_only_an_in_memory_draft(self):
  c=self.control;c.net.outgoing_code=bear.new_code();c.net.send.return_value='failed-id';c.send_letter('Тёплое письмо ♥');c.send_failed('failed-id','нет связи')
  self.assertEqual(c.letter_draft,'Тёплое письмо ♥');c.compose_letter();self.assertEqual(c.letter_composer.editor.toPlainText(),'Тёплое письмо ♥')
  import json
  saved=json.loads(bear.CONFIG.read_text());self.assertNotIn('letter_draft',saved);self.assertNotIn('Тёплое письмо',bear.CONFIG.read_text())
  c.letter_composer.close();self.assertIsNone(c.letter_composer)
 def test_message_checks_updates_but_acks_and_preview_do_not(self):
  c=self.control;c.updater=Mock();c.net.outgoing_code=bear.new_code();c.net.send.return_value='id';c.command('heart');self.assertEqual(c.updater.check.call_count,1)
  c.send_letter('Привет');self.assertEqual(c.updater.check.call_count,2)
  c.receive({'cmd':'shy','id':'incoming','sender':'partner','reply_to':bear.new_code()});self.assertEqual(c.updater.check.call_count,3)
  c.receive({'cmd':'ack','id':'ack','ref':'id'});self.assertEqual(c.updater.check.call_count,3)
  c.queue_letter('Предпросмотр');self.assertEqual(c.updater.check.call_count,3)
 def test_bear_window_stays_attached_to_selected_monitor_edge(self):
  c=self.control;geometry=app.primaryScreen().geometry()
  for side in ['left','right']:
   with patch.object(bear.random,'choice',return_value=side):c.pet.play_letter('Проверка края')
   self.assertEqual(c.pet.side,side);self.assertEqual(c.pet.width(),300)
   self.assertEqual(c.pet.x(),geometry.left() if side=='left' else geometry.right()-299)
 def test_panel_reopens_from_tray_after_minimizing_or_hiding(self):
  c=self.control
  for hidden in [False,True]:
   c.showMinimized();app.processEvents();self.assertTrue(c.isMinimized())
   if hidden:c.hide()
   c.menu.actions()[0].trigger();app.processEvents()
   self.assertTrue(c.isVisible());self.assertFalse(c.isMinimized())
  c.hide();c.menu.actions()[0].trigger();app.processEvents();self.assertTrue(c.isVisible())
  c.showMinimized();app.processEvents();c.pet.mouseDoubleClickEvent(None);app.processEvents()
  self.assertTrue(c.isVisible());self.assertFalse(c.isMinimized())
if __name__=='__main__':unittest.main()
