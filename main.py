import functools
import datetime
import wx
import wx.html2
import wx.lib.newevent
import paho.mqtt.client as paho
import threading

import printing

import gi

gi.require_version("Notify", "0.7")
from gi.repository import Notify  # noqa: E402

MqttMessageWaiting, EVT_MQTT_MESSAGE_WAITING = wx.lib.newevent.NewEvent()

DEBUG = True
NAMES = ("Rechner", "Kilte", "Dulse", "Barkley", "Oreo", "Hyena", "Fox", "Dog")
MQTT_ENABLE = False
LABEL_PRINTER = "Zebra_2824"
SCREEN_SIZE = (800, 480)

LABEL_CACHE = {}

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

        sizer0.Add(self.closeBtn, -1, wx.ALL | wx.EXPAND, 5)

        if len(NAMES) >= 1:
            btn = wx.Button(self, wx.ID_ANY, NAMES[0])
            sizer0.Add(btn, -1, wx.ALL | wx.EXPAND, 5)
            self.buttons.append(btn)

        vsizer.Add(sizer0, -1, wx.ALL | wx.EXPAND, 5)

        for n in range(1, len(NAMES), 2):
            sizer = wx.BoxSizer(wx.HORIZONTAL)
            btn = wx.Button(self, wx.ID_ANY, NAMES[n])
            self.buttons.append(btn)
            sizer.Add(btn, -1, wx.ALL | wx.EXPAND, 5)
            try:
                btn = wx.Button(self, wx.ID_ANY, NAMES[n + 1])
                self.buttons.append(btn)
                sizer.Add(btn, -1, wx.ALL | wx.EXPAND, 5)
            except IndexError:
                pass

            vsizer.Add(sizer, -1, wx.ALL | wx.EXPAND, 0)

        self.SetSizer(vsizer)
        self.SetSize(SCREEN_SIZE)
        self.Layout()


class Frame(wx.Frame):
    def __init__(self, *args, **kwargs):
        wx.Frame.__init__(self, *args, **kwargs)
        self.controls = ControlsPanel(self)
        if not DEBUG:
            self.ShowFullScreen(True)


class ControlsPanel(wx.Panel):
    def __init__(self, *args, **kwargs):
        wx.Panel.__init__(self, *args, **kwargs)


        self.Bind(wx.EVT_CLOSE, self.close)
        self.Bind(EVT_MQTT_MESSAGE_WAITING, self.processMqtt)

        sizer = wx.BoxSizer(wx.VERTICAL)
        bold = wx.Font(20, wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.BOLD, False)

        self.snipsBtn = wx.Button(self, wx.ID_ANY, "Idle")
        self.snipsBtn.Bind(wx.EVT_BUTTON, self.close)

        self.dateBtn = wx.Button(self, wx.ID_ANY, "Date Label")
        self.dateBtn.SetFont(bold)
        self.dateBtn.Bind(wx.EVT_BUTTON, self.print_date)

        self.outsideBtn = wx.Button(self, wx.ID_ANY, "Outside Label")
        self.outsideBtn.SetFont(bold)
        self.outsideBtn.Bind(wx.EVT_BUTTON, self.print_outside)

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

        vsizer_left = wx.BoxSizer(wx.VERTICAL)
        vsizer_left.Add(self.dateBtn, -1, wx.ALL | wx.EXPAND, 0)
        vsizer_left.Add(self.outsideBtn, -1, wx.ALL | wx.EXPAND, 0)

        vsizer_right = wx.BoxSizer(wx.VERTICAL)
        vsizer_right.Add(self.nameBtn, -1, wx.ALL | wx.EXPAND, 0)
        vsizer_right.Add(self.soundBtn, -1, wx.ALL | wx.EXPAND, 0)

        hsizer_top = wx.BoxSizer(wx.HORIZONTAL)
        hsizer_top.Add(vsizer_left, -1, wx.ALL | wx.EXPAND, 0)
        hsizer_top.Add(vsizer_right, -1, wx.ALL | wx.EXPAND, 0)

        sizer.Add(self.snipsBtn, -1, wx.ALL | wx.EXPAND, 0)
        sizer.Add(hsizer_top, 2, wx.ALL | wx.EXPAND, 10)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)

        sizer.Add(hsizer, 1, wx.ALL | wx.EXPAND, 10)
        hsizer.Add(self.kitchenBtn, -1, wx.ALL | wx.EXPAND, 0)
        hsizer.Add(self.diningBtn, -1, wx.ALL | wx.EXPAND, 0)
        self.SetSizer(sizer)

        self.namePanel = NamePanel(self)
        self.namePanel.Hide()
        self._bindNameButtons()

        self.printer = printing.Main(False)

        Notify.init("Snips")

        if MQTT_ENABLE:
            self.mqtt = paho.Client()
            self.mqtt.connect("10.0.10.11")
            self.mqtt.on_publish = Controls.on_publish
            self.MQTT_EXIT = threading.Event()
            self.thread = threading.Thread(target=self._mqttWorkerThread)
            self.thread.start()

            self.mqtt.subscribe("homeassistant/light/kitchen/state")
            self.mqtt.subscribe("homeassistant/light/dining_room/state")

        self.buttons = {
            "homeassistant/light/kitchen/state": self.kitchenBtn,
            "homeassistant/light/dining_room/state": self.diningBtn,
        }


    def print_date(self, event):
        self.print_using_cache("date")


    def print_using_cache(self, theme, **kwargs):
        # Check cache first:
        today = datetime.datetime.now().date()
        cache_key = theme
        if cache_key in LABEL_CACHE:
            if LABEL_CACHE[cache_key]['date'] == today:
                # Use cached label
                self.printer.pdf = LABEL_CACHE[cache_key]['pdf']
                self.printer.printout(printer=LABEL_PRINTER)
                return

            else:
                # Delete old label from cache
                self.printer.cleanup([LABEL_CACHE[cache_key]['pdf']])

        # Generate new label
        self.printer.nametag(theme=theme, **kwargs)
        if DEBUG:
            self.printer.preview()
        else:
            self.printer.printout(printer=LABEL_PRINTER)
        # Add to cache
        LABEL_CACHE[cache_key] = {
            "pdf": self.printer.pdf,
            "date": today,
        }


    def show_name_menu(self, event):
        #self.Hide()
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
        self.print_using_cache("name", name=label)
        self.hide_name_menu(event=None)


    def print_outside(self, event):
        self.print_using_cache("outside")


    @staticmethod
    def on_publish(client, userdata, result):
        print("Published: {0}: {1}".format(userdata, result))

    def send_notification(self, title, text, icon="dialog-information"):
        pass
        # subprocess.check_call(['/usr/bin/notify-send', str(title), str(text)])
        # self.notification = Notify.Notification.new(title, text)
        # self.notification.show()
        # Since we might not be on the main thread (?)
        # wx.CallAfter(self.queue_close_notifiaction)

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


    def processMqtt(self, event):
        try:
            button = self.buttons[event.topic]
        except KeyError:
            print(
                "No matching button for registered event topic: {0}".format(event.topic)
            )
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
        if MQTT_ENABLE:
            self.MQTT_EXIT.set()
            self.thread.join()
            self.mqtt.disconnect()
        self.Destroy()


if __name__ == "__main__":
    app = wx.App()
    frame = Frame(None, title="Kitchen", size=SCREEN_SIZE)
    frame.Show()
    app.MainLoop()
