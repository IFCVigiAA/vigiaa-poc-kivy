from kivymd.app import MDApp
from kivy.lang import Builder
from kivymd.uix.screen import MDScreen
from kivymd.uix.snackbar import Snackbar
from kivy.clock import mainthread, Clock
from kivy.utils import platform
import requests
import threading

# Importações do Android nativo (A Mágica do Pyjnius)
if platform == 'android':
    from jnius import autoclass, java_method, PythonJavaClass
    from android.permissions import request_permissions, Permission
    
    Context = autoclass('android.content.Context')
    LocationManager = autoclass('android.location.LocationManager')
    Looper = autoclass('android.os.Looper')
    PythonActivity = autoclass('org.kivy.android.PythonActivity')

    class LocationListener(PythonJavaClass):
        __javainterfaces__ = ['android/location/LocationListener']

        def __init__(self, callback):
            super().__init__()
            self.callback = callback

        @java_method('(Landroid/location/Location;)V')
        def onLocationChanged(self, location):
            # Quando o Android achar a coordenada, manda pro Python
            self.callback(location.getLatitude(), location.getLongitude())

        @java_method('(Ljava/lang/String;)V')
        def onProviderDisabled(self, provider): pass

        @java_method('(Ljava/lang/String;)V')
        def onProviderEnabled(self, provider): pass

        @java_method('(Ljava/lang/String;ILandroid/os/Bundle;)V')
        def onStatusChanged(self, provider, status, extras): pass

KV = '''
<FocusFormScreen>:
    md_bg_color: 1, 1, 1, 1

    MDBoxLayout:
        orientation: "vertical"

        MDTopAppBar:
            title: "VigiAA - GPS Preciso"
            md_bg_color: 1, 1, 1, 1
            specific_text_color: 0, 0, 0, 1
            elevation: 1

        ScrollView:
            MDBoxLayout:
                orientation: "vertical"
                padding: "20dp"
                spacing: "15dp"
                adaptive_height: True

                MDRaisedButton:
                    id: btn_gps
                    text: "Capturar Localização Exata"
                    icon: "crosshairs-gps"
                    md_bg_color: "#39BFEF"
                    text_color: 1, 1, 1, 1
                    size_hint_x: 1
                    on_release: root.iniciar_gps()

                MDLabel:
                    id: lbl_gps_status
                    text: "Aguardando..."
                    halign: "center"
                    theme_text_color: "Hint"
                    font_style: "Caption"

                MDTextField:
                    id: tf_cidade
                    hint_text: "Cidade"

                MDTextField:
                    id: tf_bairro
                    hint_text: "Bairro"

                MDTextField:
                    id: tf_rua
                    hint_text: "Rua"

                MDTextField:
                    id: tf_cep
                    hint_text: "CEP"
'''

class FocusFormScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.gps_ativo = False
        self.location_manager = None
        self.listener = None

    def iniciar_gps(self):
        if self.gps_ativo:
            return

        self.ids.btn_gps.text = "Acessando sensores..."
        self.ids.btn_gps.disabled = True
        
        if platform == 'android':
            request_permissions([Permission.ACCESS_FINE_LOCATION, Permission.ACCESS_COARSE_LOCATION], self.gps_callback)
        else:
            self.mostrar_aviso("O GPS Nativo só funciona no celular.")
            self.ids.btn_gps.text = "Capturar Localização Exata"
            self.ids.btn_gps.disabled = False

    def gps_callback(self, permissions, results):
        if all(results):
            Clock.schedule_once(self.ligar_antena_nativa, 0)
        else:
            self.mostrar_aviso("Permissão negada.")
            self.ids.btn_gps.text = "Capturar Localização Exata"
            self.ids.btn_gps.disabled = False

    @mainthread
    def ligar_antena_nativa(self, dt):
        self.ids.btn_gps.text = "Triangulando posição..."
        self.ids.btn_gps.md_bg_color = "#FF9800"
        self.gps_ativo = True

        try:
            activity = PythonActivity.mActivity
            self.location_manager = activity.getSystemService(Context.LOCATION_SERVICE)
            self.listener = LocationListener(self.on_location_nativa)
            
            providers = self.location_manager.getProviders(True)
            if not providers:
                self.mostrar_aviso("Ligue a Localização (GPS) do celular!")
                self.parar_gps()
                return

            # Aqui é o pulo do gato: Pede a localização pela REDE (Rápido e super preciso)
            if self.location_manager.isProviderEnabled(LocationManager.NETWORK_PROVIDER):
                self.location_manager.requestLocationUpdates(
                    LocationManager.NETWORK_PROVIDER, 
                    1000, 1.0, 
                    self.listener, 
                    Looper.getMainLooper()
                )
            
            # E pede pelo SATÉLITE simultaneamente (O que responder primeiro ganha)
            if self.location_manager.isProviderEnabled(LocationManager.GPS_PROVIDER):
                self.location_manager.requestLocationUpdates(
                    LocationManager.GPS_PROVIDER, 
                    1000, 1.0, 
                    self.listener, 
                    Looper.getMainLooper()
                )

        except Exception as e:
            self.mostrar_aviso(f"Erro nativo: {e}")
            self.parar_gps()

    def on_location_nativa(self, lat, lon):
        # Achou a localização! Desliga a antena pra não drenar a bateria
        self.parar_gps()
        Clock.schedule_once(lambda dt: self.processar_coordenadas(lat, lon), 0)

    def parar_gps(self):
        if self.location_manager and self.listener:
            self.location_manager.removeUpdates(self.listener)
        self.gps_ativo = False

    def processar_coordenadas(self, lat, lon):
        self.ids.btn_gps.text = "Localização Exata Capturada!"
        self.ids.btn_gps.icon = "check"
        self.ids.btn_gps.md_bg_color = "#4CAF50" # Verde
        self.ids.lbl_gps_status.text = f"Lat: {lat:.5f} | Lon: {lon:.5f}"
        
        # Manda a latitude e longitude pro satélite aberto traduzir na rua
        threading.Thread(target=self.traduzir_coordenada, args=(lat, lon)).start()

    def traduzir_coordenada(self, lat, lon):
        try:
            headers = {'User-Agent': 'VigiAA_PoC/1.0'}
            url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=18&addressdetails=1"
            res = requests.get(url, headers=headers).json()
            addr = res.get("address", {})
            self.atualizar_campos_gps(addr)
        except:
            self.mostrar_aviso("Sem internet para traduzir a rua.")

    @mainthread
    def atualizar_campos_gps(self, addr):
        # O OpenStreetMap retorna a cidade em um desses 3 campos
        self.ids.tf_cidade.text = addr.get("city", addr.get("town", addr.get("village", "")))
        
        # O Bairro pode vir com esses 3 nomes diferentes
        bairro = addr.get("suburb", addr.get("neighbourhood", addr.get("district", "")))
        self.ids.tf_bairro.text = bairro
        
        # A rua
        self.ids.tf_rua.text = addr.get("road", "")
        self.ids.tf_cep.text = addr.get("postcode", "")
        
        self.ids.btn_gps.disabled = False

    @mainthread
    def mostrar_aviso(self, texto):
        Snackbar(text=texto).open()

class VigiAAPoCApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "LightBlue"
        Builder.load_string(KV)
        return FocusFormScreen()

if __name__ == "__main__":
    VigiAAPoCApp().run()
