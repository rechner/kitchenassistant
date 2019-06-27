import wx
import paho.mqtt.client as paho

import printing

class Controls(wx.Frame):
    def __init__(self, *args, **kwargs):
        wx.Frame.__init__(self, *args, **kwargs)

        self.Bind(wx.EVT_CLOSE, self.close)

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.printBtn = wx.Button(self, wx.ID_ANY, "Print Date Label")
        self.printBtn.SetFont(wx.Font(20, wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.BOLD, False))
        self.printBtn.Bind(wx.EVT_BUTTON, self.print_date)

        self.kitchenBtn = wx.Button(self, wx.ID_ANY, "Kitchen Lights")
        self.kitchenBtn.SetFont(wx.Font(20, wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.NORMAL, False))
        self.kitchenBtn.Bind(wx.EVT_BUTTON, self.toggle_kitchen)

        self.diningBtn = wx.Button(self, wx.ID_ANY, "Dining Lights")
        self.diningBtn.SetFont(wx.Font(20, wx.FONTFAMILY_DEFAULT, wx.NORMAL, wx.NORMAL, False))
        self.diningBtn.Bind(wx.EVT_BUTTON, self.toggle_dining)


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
        self.mqtt.loop_start()

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


    def close(self, event):
        self.mqtt.loop_stop()
        self.mqtt.disconnect()
        self.Destroy()

if __name__ == '__main__':
    app = wx.App()
    frame = Controls(None, title="Kitchen", size=(480, 320))
    frame.Show()
    app.MainLoop()
