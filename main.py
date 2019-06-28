import wx
import wx.lib.newevent
import paho.mqtt.client as paho
import threading

import printing

MqttMessageWaiting, EVT_MQTT_MESSAGE_WAITING = wx.lib.newevent.NewEvent()

class Controls(wx.Frame):
    def __init__(self, *args, **kwargs):
        wx.Frame.__init__(self, *args, **kwargs)

        self.Bind(wx.EVT_CLOSE, self.close)
        self.Bind(EVT_MQTT_MESSAGE_WAITING, self.processMqtt)

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.printBtn = wx.Button(self, wx.ID_ANY, "Print Date Label")
        self.printBtn.SetFont(wx.Font(20, wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.BOLD, False))
        self.printBtn.Bind(wx.EVT_BUTTON, self.print_date)

        self.kitchenBtn = wx.Button(self, wx.ID_ANY, "Kitchen Lights")
        self.kitchenBtn.SetFont(wx.Font(20, wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.NORMAL, False))
        self.kitchenBtn.Bind(wx.EVT_BUTTON, self.toggle_kitchen)
        self.kitchenBtn.SetBackgroundColour("#275DAD")
        self.kitchenBtn.SetForegroundColour("white")

        self.diningBtn = wx.Button(self, wx.ID_ANY, "Dining Lights")
        self.diningBtn.SetFont(wx.Font(20, wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.NORMAL, False))
        self.diningBtn.Bind(wx.EVT_BUTTON, self.toggle_dining)
        self.diningBtn.SetBackgroundColour("#C1292E")
        self.diningBtn.SetForegroundColour("white")


        self.SetBackgroundColour("black")
        self.ShowFullScreen(True)

        sizer.Add(self.printBtn, 2, wx.ALL|wx.EXPAND|wx.ALIGN_CENTRE, 20)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        sizer.Add(hsizer, 1, wx.ALL|wx.EXPAND, 20)
        hsizer.Add(self.kitchenBtn, -1, wx.ALL|wx.EXPAND|wx.ALIGN_CENTRE, 0)
        hsizer.Add(self.diningBtn, -1, wx.ALL|wx.EXPAND|wx.ALIGN_CENTRE, 0)
        self.SetSizer(sizer)

        self.printer = printing.Main(False)

        self.mqtt = paho.Client()
        self.mqtt.connect("10.0.10.11")
        self.mqtt.on_publish = Controls.on_publish
        self.MQTT_EXIT = threading.Event()
        self.thread = threading.Thread(target=self._mqttWorkerThread)
        self.thread.start()
        
        self.mqtt.subscribe("homeassistant/light/kitchen/state")
        self.mqtt.subscribe("homeassistant/light/dining_room/state")

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
    
    @staticmethod
    def on_publish(client, userdata, result):
        print("Published: {0}: {1}".format(userdata, result))

  
    def toggle_kitchen(self, event):
        print("Kitchen light toggle")
        self.mqtt.publish("house/switch/kitchen", "toggle")

    def toggle_dining(self, event):
        print("Dining light toggle")
        self.mqtt.publish("house/switch/dining_room", "toggle")

    def processMqtt(self, event):
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
        self.MQTT_EXIT.set()
        self.thread.join()
        self.mqtt.disconnect()
        self.Destroy()

if __name__ == '__main__':
    app = wx.App()
    frame = Controls(None, title="Kitchen", size=(480, 320))
    frame.Show()
    app.MainLoop()
