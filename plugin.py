# Tronity Python Plugin
#
# Author: flopp999
#
"""
<plugin key="Tronity" name="Tronity 0.24" author="flopp999" version="0.24" wikilink="https://github.com/flopp999/Tronity-Domoticz" externallink="https://www.tronity.io">
    <description>
        <h2>Support me with a coffee &<a href="https://www.buymeacoffee.com/flopp999">https://www.buymeacoffee.com/flopp999</a></h2><br/>
        <h2>or use my Tibber link &<a href="https://tibber.com/se/invite/8af85f51">https://tibber.com/se/invite/8af85f51</a></h2><br/>
        <h2>If you want to get 2 extra trial weeks and at the same time support me, please use this link &<a href="https://app.tronity.io/signup/9ZVleQDQu">https://app.tronity.io/signup/9ZVleQDQu</a></h2><br/>
        <h3>Configuration</h3>
        <h4>Use Client Id and Client Secret from Tronity Platform &<a href="https://app.platform.tronity.io/apps">https://app.platform.tronity.io/apps</a></h4><br/>
    </description>
    <params>
        <param field="Mode1" label="Client Id" width="320px" required="true" default="Id"/>
        <param field="Mode2" label="Client Secret" password="true" width="350px" required="true" default="Secret"/>
        <param field="Mode6" label="Debug to file (Tronity.log)" width="70px">
            <options>
                <option label="Yes" value="Yes" />
                <option label="No" value="No" />
            </options>
        </param>
    </params>
</plugin>
"""

import Domoticz

Package = True

try:
    import requests, json, os, logging
except ImportError as e:
    Package = False

try:
    from logging.handlers import RotatingFileHandler
except ImportError as e:
    Package = False

try:
    from datetime import datetime, timedelta
except ImportError as e:
    Package = False

dir = os.path.dirname(os.path.realpath(__file__))
logger = logging.getLogger("Tronity")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(dir+'/Tronity.log', maxBytes=1000000, backupCount=5)
logger.addHandler(handler)

class BasePlugin:
    enabled = False

    def __init__(self):
        self.token = ''
        self.loop = 0
        self.Count = 5
        self.CarIds = []
        self.FirstError = True
        return

    def onStart(self):
#        Domoticz.Debugging(128)
        WriteDebug("===onStart===")
        self.Id = Parameters["Mode1"]
        self.Secret = Parameters["Mode2"]

        if len(self.Id) != 36:
            Domoticz.Log("Identifier too short")
            WriteDebug("Identifier too short")

        if len(self.Secret) < 4:
            Domoticz.Log("Secret too short")
            WriteDebug("Secret too short")

        if os.path.isfile(dir+'/Tronity.zip'):
            if 'Tronity' not in Images:
                Domoticz.Image('Tronity.zip').Create()
            self.ImageID = Images["Tronity"].ID

        self.GetToken = Domoticz.Connection(Name="Get Token", Transport="TCP/IP", Protocol="HTTPS", Address="api-eu.tronity.io", Port="443")
        self.GetData = Domoticz.Connection(Name="Get Data", Transport="TCP/IP", Protocol="HTTPS", Address="api-eu.tronity.io", Port="443")
        self.GetID = Domoticz.Connection(Name="Get ID", Transport="TCP/IP", Protocol="HTTPS", Address="api-eu.tronity.io", Port="443")

    def onDisconnect(self, Connection):
        WriteDebug("onDisconnect called for connection '"+Connection.Name+"'.")

    def onConnect(self, Connection, Status, Description):
        WriteDebug("onConnect")
        WriteDebug("Test av Status")
        WriteDebug(str(Status))
        if CheckInternet() == True:
            if (Status == 0):

                if Connection.Name == ("Get Token"):
                    WriteDebug("Get Token")
                    data = "{ \"grant_type\":\"app\", \"client_id\":\""+self.Id+"\", \"client_secret\":\""+self.Secret+"\"}"
                    headers = {'Host': 'api-eu.tronity.io', 'Content-Type': 'application/json'}
                    Connection.Send({'Verb':'POST', 'URL': '/oauth/authentication', 'Headers': headers, 'Data': data})

                elif Connection.Name == ("Get ID"):
                    if self.token == "":
                        self.GetID.Disconnect()
                        Domoticz.Log("Missing Token, will try to get it")
                        self.GetToken.Connect()
                    WriteDebug("Get ID")
                    headers = { 'Host': 'api-eu.tronity.io', 'Authorization': 'Bearer '+self.token}
                    Connection.Send({'Verb':'GET', 'URL': '/v1/vehicles', 'Headers': headers})

                elif Connection.Name == ("Get Data"):
                    if self.CarIds == []:
                        self.GetData.Disconnect()
                        Domoticz.Log("Missing Car ID, will try to get it")
                        self.GetToken.Connect()
                    WriteDebug("Get Data")
                    headers = { 'Host': 'api-eu.tronity.io', 'Authorization': 'Bearer '+self.token}
                    for CarId in self.CarIds:
                        Connection.Send({'Verb':'GET', 'URL': '/v1/vehicles/'+CarId+'/bulk', 'Headers': headers})



    def onMessage(self, Connection, Data):
#        Domoticz.Log(str(Data))
        Status = int(Data["Status"])

        if Status == 200 or Status == 201:
            Data = Data['Data'].decode('UTF-8')
            Data = json.loads(Data)

            if Connection.Name == ("Get Token"):
                self.token = Data["access_token"]
                self.GetToken.Disconnect()
                Domoticz.Log("Token received")
                self.GetID.Connect()

            elif Connection.Name == ("Get ID"):
                self.CarIds=[]
                for each in Data["data"]:
                    self.CarIds.append(each["id"])
                self.GetID.Disconnect()
                Domoticz.Log("Car ID received")
                Domoticz.Log(str(self.CarIds))
                self.GetData.Connect()

            elif Connection.Name == ("Get Data"):
                for name,value in Data.items():
                    Domoticz.Log(str(name))
                    Domoticz.Log(str(value))
                    UpdateDevice(str(value), name)
                self.GetData.Disconnect()
                Domoticz.Log("Data Updated")

        elif Status == 401 and self.FirstError == True:
            Domoticz.Error("first")
            self.FirstError = False

            if _plugin.GetToken.Connected():
                Domoticz.Error("GetToken")
                _plugin.GetToken.Disconnect()

            if _plugin.GetData.Connected():
                Domoticz.Error("GetData")
                _plugin.GetData.Disconnect()

            if _plugin.GetID.Connected():
                Domoticz.Error("GetID")
                _plugin.GetID.Disconnect()
            self.GetToken.Connect()

#        elif Status == 500:
#            Domoticz.Error("Is your Client ID 36 characters long?")


        else:
            WriteDebug("Status = "+str(Status))
            Domoticz.Error(str("Status "+str(Status)))
            Domoticz.Error(str(Data))
            if _plugin.GetToken.Connected():
                _plugin.GetToken.Disconnect()
            if _plugin.GetData.Connected():
                _plugin.GetData.Disconnect()
            if _plugin.GetID.Connected():
                _plugin.GetID.Disconnect()


    def onHeartbeat(self):
        self.Count += 1
        if self.Count == 6 and not self.GetData.Connected() and not self.GetData.Connecting():
            self.GetData.Connect()
            WriteDebug("onHeartbeat")
            self.Count = 0

global _plugin
_plugin = BasePlugin()

def onStart():
    global _plugin
    _plugin.onStart()

def UpdateDevice(sValue, Name):
    if Name == "odometer":
        ID = 1
        Unit = ""
    if Name == "range":
        ID = 2
        Unit = "km"
    if Name == "level":
        ID = 3
        Unit = "%"
    if Name == "charging":
        ID = 4
        if sValue == "Charging":
            sValue = 1
        if sValue == "Disconnected":
            sValue = 0
        Unit = ""
    if Name == "latitude":
        ID = 5
        Unit = ""
    if Name == "longitude":
        ID = 6
        Unit = ""
    if Name == "timestamp":
        ID = 7
#        sValue = timedelta(milliseconds=int(sValue))
#        Domoticz.Log(str(sValue))
        Unit = ""
    if (ID in Devices):
        if Devices[ID].sValue != sValue:
            Devices[ID].Update(0, str(sValue))

    if (ID not in Devices):
        if sValue == "-32768":
            Used = 0
        else:
            Used = 1
        Domoticz.Device(Name=Name, Unit=ID, TypeName="Custom", Options={"Custom": "0;"+Unit}, Used=1, Image=(_plugin.ImageID)).Create()

def CheckInternet():
    WriteDebug("Entered CheckInternet")
    try:
        WriteDebug("Ping")
        requests.get(url='https://api-eu.tronity.io/', timeout=2)
        WriteDebug("Internet is OK")
        return True
    except:
        if _plugin.GetToken.Connected() or _plugin.GetToken.Connecting():
            _plugin.GetToken.Disconnect()
        if _plugin.GetData.Connected() or _plugin.GetData.Connecting():
            _plugin.GetData.Disconnect()
        if _plugin.GetID.Connected() or _plugin.GetID.Connecting():
            _plugin.GetID.Disconnect()

        WriteDebug("Internet is not available")
        return False

def WriteDebug(text):
    if Parameters["Mode6"] == "Yes":
        timenow = (datetime.now())
        logger.info(str(timenow)+" "+text)

def onConnect(Connection, Status, Description):
    global _plugin
    _plugin.onConnect(Connection, Status, Description)

def onDisconnect(Connection):
    global _plugin
    _plugin.onDisconnect(Connection)

def onMessage(Connection, Data):
    _plugin.onMessage(Connection, Data)

def onHeartbeat():
    global _plugin
    _plugin.onHeartbeat()

    # Generic helper functions
def DumpConfigToLog():
    for x in Parameters:
        if Parameters[x] != "":
            Domoticz.Debug( "'" + x + "':'" + str(Parameters[x]) + "'")
    Domoticz.Debug("Device count: " + str(len(Devices)))
    for x in Devices:
        Domoticz.Debug("Device:           " + str(x) + " - " + str(Devices[x]))
        Domoticz.Debug("Device ID:       '" + str(Devices[x].ID) + "'")
        Domoticz.Debug("Device Name:     '" + Devices[x].Name + "'")
        Domoticz.Debug("Device nValue:    " + str(Devices[x].nValue))
        Domoticz.Debug("Device sValue:   '" + Devices[x].sValue + "'")
        Domoticz.Debug("Device LastLevel: " + str(Devices[x].LastLevel))
    return
