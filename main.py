import functools
import wx
import wx.lib.newevent
import paho.mqtt.client as paho
import threading
import json
#import subprocess

import printing

import gi
gi.require_version('Notify', '0.7')
from gi.repository import Notify

MqttMessageWaiting, EVT_MQTT_MESSAGE_WAITING = wx.lib.newevent.NewEvent()

NAMES = ("Rechner", "Barkley", "Odysseus", "Adam", "Robyn", "Spritz")

class NamePanel(wx.Panel):
    def __init__(self, *args, **kwargs):
        wx.Panel.__init__(self, *args, **kwargs)
        self.SetBackgroundColour("black")
        self.buttons = []

        vsizer = wx.BoxSizer(wx.VERTICAL)

        bold = wx.Font(16, wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.BOLD, False)

        sizer0 = wx.BoxSizer(wx.HORIZONTAL)
        self.closeBtn = wx.Button(self, wx.ID_ANY, "< Main Menu")
        self.closeBtn.SetFont(bold)
        self.closeBtn.SetBackgroundColour("red")

        sizer0.Add(self.closeBtn, -1, wx.ALL|wx.EXPAND|wx.ALIGN_CENTRE, 5)

        if len(NAMES) >= 1:
            btn = wx.Button(self, wx.ID_ANY, NAMES[0])
            sizer0.Add(btn, -1, wx.ALL|wx.EXPAND|wx.ALIGN_CENTRE, 5)
            self.buttons.append(btn)

        vsizer.Add(sizer0, -1, wx.ALL|wx.EXPAND|wx.ALIGN_CENTRE, 5)

        for n in range(1, len(NAMES), 2):
            sizer = wx.BoxSizer(wx.HORIZONTAL)
            btn = wx.Button(self, wx.ID_ANY, NAMES[n])
            self.buttons.append(btn)
            sizer.Add(btn, -1, wx.ALL|wx.EXPAND|wx.ALIGN_CENTRE, 5)
            try:
                btn = wx.Button(self, wx.ID_ANY, NAMES[n+1])
                self.buttons.append(btn)
                sizer.Add(btn, -1, wx.ALL|wx.EXPAND|wx.ALIGN_CENTRE, 5)
            except IndexError:
                pass

            vsizer.Add(sizer, -1, wx.ALL|wx.EXPAND, 0)

        self.SetSizer(vsizer)
        self.SetSize((480, 320))
        self.Layout()


class Controls(wx.Frame):
    def __init__(self, *args, **kwargs):
        wx.Frame.__init__(self, *args, **kwargs)

        self.Bind(wx.EVT_CLOSE, self.close)
        self.Bind(EVT_MQTT_MESSAGE_WAITING, self.processMqtt)

        self.namePanel = NamePanel(self)
        self.namePanel.Hide()
        self._bindNameButtons()

        sizer = wx.BoxSizer(wx.VERTICAL)
        bold = wx.Font(20, wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.BOLD, False)

        self.snipsBtn = wx.Button(self, wx.ID_ANY, "Idle")

        self.printBtn = wx.Button(self, wx.ID_ANY, "Date Label")
        self.printBtn.SetFont(bold)
        self.printBtn.Bind(wx.EVT_BUTTON, self.print_date)
        
        self.nameBtn = wx.Button(self, wx.ID_ANY, "Name Label")
        self.nameBtn.SetFont(bold)
        self.nameBtn.Bind(wx.EVT_BUTTON, self.show_name_menu)

        self.kitchenBtn = wx.Button(self, wx.ID_ANY, "Kitchen Lights")
        self.kitchenBtn.SetFont(bold)
        self.kitchenBtn.Bind(wx.EVT_BUTTON, self.toggle_kitchen)
        self.kitchenBtn.SetBackgroundColour("#275DAD")
        self.kitchenBtn.SetForegroundColour("white")

        self.diningBtn = wx.Button(self, wx.ID_ANY, "Dining Lights")
        self.diningBtn.SetFont(bold)
        self.diningBtn.Bind(wx.EVT_BUTTON, self.toggle_dining)
        self.diningBtn.SetBackgroundColour("#C1292E")
        self.diningBtn.SetForegroundColour("white")


        self.SetBackgroundColour("black")
        self.ShowFullScreen(True)

        hsizer_top = wx.BoxSizer(wx.HORIZONTAL)
        hsizer_top.Add(self.printBtn, -1, wx.ALL|wx.EXPAND|wx.ALIGN_CENTRE, 0)
        hsizer_top.Add(self.nameBtn, -1, wx.ALL|wx.EXPAND|wx.ALIGN_CENTRE, 0)

        sizer.Add(self.snipsBtn, -1, wx.ALL|wx.EXPAND|wx.ALIGN_CENTRE, 0)
        sizer.Add(hsizer_top, 2, wx.ALL|wx.EXPAND|wx.ALIGN_CENTRE, 20)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        sizer.Add(hsizer, 1, wx.ALL|wx.EXPAND, 20)
        hsizer.Add(self.kitchenBtn, -1, wx.ALL|wx.EXPAND|wx.ALIGN_CENTRE, 0)
        hsizer.Add(self.diningBtn, -1, wx.ALL|wx.EXPAND|wx.ALIGN_CENTRE, 0)
        self.SetSizer(sizer)

        self.printer = printing.Main(False)

        Notify.init("Snips")

        self.mqtt = paho.Client()
        self.mqtt.connect("10.0.10.11")
        self.mqtt.on_publish = Controls.on_publish
        self.MQTT_EXIT = threading.Event()
        self.thread = threading.Thread(target=self._mqttWorkerThread)
        self.thread.start()
        
        self.mqtt.subscribe("homeassistant/light/kitchen/state")
        self.mqtt.subscribe("homeassistant/light/dining_room/state")
        self.mqtt.subscribe("hermes/dialogueManager/#")

        self.buttons = {
            'homeassistant/light/kitchen/state'     : self.kitchenBtn,
            'homeassistant/light/dining_room/state' : self.diningBtn
        }
        #self.mqtt.loop_start()

    def print_date(self, event):
        self.printer.nametag(theme='date')
        self.printer.printout(printer='Zebra_2824')
        #self.printer.preview()
        print(self.printer.pdf)
        wx.CallLater(4000, self.printer.cleanup, [self.printer.pdf,])

    def show_name_menu(self, event):
        self.namePanel.Show()

    def hide_name_menu(self, event):
        self.namePanel.Enable()
        self.namePanel.Hide()
    
    def _bindNameButtons(self):
        self.namePanel.closeBtn.Bind(wx.EVT_BUTTON, self.hide_name_menu)
        for btn in self.namePanel.buttons:
            label = btn.GetLabel()
            func = functools.partial(self.print_name, label=label)
            btn.Bind(wx.EVT_BUTTON, func)
    
    def print_name(self, event, label):
        print(label)
        self.printer.nametag(theme='name', name=label)
        self.printer.printout(printer='Zebra_2824')
        #self.printer.preview()
        print(self.printer.pdf)
        wx.CallLater(4000, self.printer.cleanup, [self.printer.pdf,])

        self.hide_name_menu(event=None)
        #self.namePanel.Disable()
        #wx.CallLater(4000, self.hide_name_menu)


    
    @staticmethod
    def on_publish(client, userdata, result):
        print("Published: {0}: {1}".format(userdata, result))

    def send_notification(self, title, text, icon="dialog-information"):
        #subprocess.check_call(['/usr/bin/notify-send', str(title), str(text)])
        self.notification = Notify.Notification.new(title, text)
        self.notification.show()
        # Since we might not be on the main thread (?)
        wx.CallAfter(self.queue_close_notifiaction)

    def queue_close_notifiaction(self, event=None):
        wx.CallLater(20000, self.close_notification)

    def close_notification(self, event=None):
        self.notification.close() 
  
    def toggle_kitchen(self, event):
        print("Kitchen light toggle")
        self.mqtt.publish("house/switch/kitchen", "toggle")

    def toggle_dining(self, event):
        print("Dining light toggle")
        self.mqtt.publish("house/switch/dining_room", "toggle")

    def snips_idle(self):
        self.snipsBtn.SetBackgroundColour("white")
        self.snipsBtn.SetForegroundColour("black")
        self.snipsBtn.SetLabelText("Idle...")

    def processHermes(self, event):
        try:
            payload = json.loads(event.payload)
        except:
            payload = {}
        if event.topic == "hermes/dialogueManager/sessionStarted":
            self.snipsBtn.SetBackgroundColour("green")
            self.snipsBtn.SetForegroundColour("white")
            self.snipsBtn.SetLabelText("Listening...")
        if event.topic == "hermes/dialogueManager/sessionEnded":
            if 'termination' in payload.keys():
                if payload['termination']['reason'] in ('timeout', 'intentNotRecognized'):
                    self.send_notification("Snips", "Sorry, I didn't quite catch that")
            self.snips_idle()

        if event.topic == "hermes/dialogueManager/endSession":
            if 'text' in payload.keys():
                print(payload['text'])
                self.send_notification("Snips", payload['text'])

    def processMqtt(self, event):
        if event.topic.startswith("hermes"):
            self.processHermes(event)
            return

        try:
            button = self.buttons[event.topic]
        except KeyError:
            print("No matching button for registered event topic: {0}".format(event.topic))
            return
        
        if event.payload == "on":
            button.SetBackgroundColour("green")
        elif event.payload == "off":
            button.SetBackgroundColour("red")

    def _mqttWorkerThread(self):
        def on_message(client, userdata, msg):
            print(msg.topic, msg.payload)
            event = MqttMessageWaiting(topic=msg.topic, payload=msg.payload)
            self.GetEventHandler().ProcessEvent(event)

        self.mqtt.on_message = on_message
        while True:
            self.mqtt.loop()
            if self.MQTT_EXIT.isSet():
                return None


    def close(self, event):
        Notify.uninit()
        self.MQTT_EXIT.set()
        self.thread.join()
        self.mqtt.disconnect()
        self.Destroy()

if __name__ == '__main__':
    app = wx.App()
    frame = Controls(None, title="Kitchen", size=(480, 320))
    frame.Show()
    app.MainLoop()
