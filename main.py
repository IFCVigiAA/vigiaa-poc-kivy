from kivymd.app import MDApp
from kivy.lang import Builder
from kivymd.uix.screen import MDScreen
from kivy.clock import mainthread, Clock
from kivy.utils import platform
import requests
import threading

if platform == 'android':
    from jnius import autoclass, java_method, PythonJavaClass
    from android.permissions import request_permissions, Permission
    
    Context = autoclass('android.content.Context')
    LocationManager = autoclass('android.location.LocationManager')
    Looper = autoclass('android.os.Looper')
    PythonActivity = autoclass('org.kivy.android.PythonActivity')

    class LocationListener(PythonJavaClass):
        __javainterfaces__ = ['android/location/LocationListener']

        def __init__(self, callback, log_func):
            super().__init__()
            self.callback = callback
            self.log_func = log_func

        @java_method('(Landroid/location/Location;)V')
        def onLocationChanged(self, location):
            self.log_func("Sensor disparou! Recebendo dados...")
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
            title: "VigiAA - Debug GPS"
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
                    text: "Testar Localização"
                    icon: "bug"
                    md_bg_color: "#39BFEF"
                    text_color: 1, 1, 1, 1
                    size_hint_x: 1
                    on_release: root.iniciar_gps()

                MDTextField:
                    id: tf_rua
                    hint_text: "Resultado Rua"

                MDTextField:
                    id: tf_bairro
                    hint_text: "Resultado Bairro"

                MDLabel:
                    text: "Console de Debug:"
                    font_style: "Caption"
                    theme_text_color: "Hint"

                # CAIXA DE TERMINAL PARA VER O QUE ESTÁ ACONTECENDO
                TextInput:
                    id: txt_log
                    size_hint_y: None
                    height: "200dp"
                    readonly: True
                    background_color: 0, 0, 0, 1
                    foreground_color: 0, 1, 0, 1  # Letra verde tipo Matrix
                    font_size: "12sp"
                    text: "Pronto para iniciar...\\n"
'''

class FocusFormScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.gps_ativo = False
        self.location_manager = None
        self.listener = None

    @mainthread
    def log(self, texto):
        self.ids.txt_log.text += f"> {texto}\\n"
        print(texto)

    def iniciar_gps(self):
        if self.gps_ativo:
            return
            
        self.ids.txt_log.text = "" # Limpa o log
        self.log("Botão pressionado.")
        self.ids.btn_gps.disabled = True
        
        if platform == 'android':
            self.log("Pedindo permissão ao Android...")
            request_permissions([Permission.ACCESS_FINE_LOCATION, Permission.ACCESS_COARSE_LOCATION], self.gps_callback)
        else:
            self.log("Erro: Teste sendo feito no PC.")
            self.ids.btn_gps.disabled = False

    def gps_callback(self, permissions, results):
        if all(results):
            self.log("Permissão CONCEDIDA.")
            Clock.schedule_once(self.ligar_antena_nativa, 0)
        else:
            self.log("Permissão NEGADA pelo usuário.")
            self.ids.btn_gps.disabled = False

    @mainthread
    def ligar_antena_nativa(self, dt):
        self.ids.btn_gps.text = "Lendo Sensores..."
        self.gps_ativo = True

        try:
            self.log("Iniciando PythonActivity...")
            activity = PythonActivity.mActivity
            self.location_manager = activity.getSystemService(Context.LOCATION_SERVICE)
            self.listener = LocationListener(self.on_location_nativa, self.log)
            
            # 1. VERIFICA PROVEDORES LIGADOS
            providers = self.location_manager.getProviders(True).toArray()
            providers_list = [p for p in providers]
            self.log(f"Provedores ativos: {providers_list}")

            if not providers_list:
                self.log("ERRO: Nenhum sensor ativo. Ligue o GPS!")
                self.parar_gps()
                return

            # 2. TENTA O CACHE INSTANTÂNEO (O TRUQUE DO UBER)
            self.log("Buscando no cache rápido...")
            loc_net = self.location_manager.getLastKnownLocation(LocationManager.NETWORK_PROVIDER)
            if loc_net:
                self.log("Cache de REDE encontrado!")
                self.on_location_nativa(loc_net.getLatitude(), loc_net.getLongitude())
                return
                
            loc_gps = self.location_manager.getLastKnownLocation(LocationManager.GPS_PROVIDER)
            if loc_gps:
                self.log("Cache de GPS encontrado!")
                self.on_location_nativa(loc_gps.getLatitude(), loc_gps.getLongitude())
                return

            # 3. SE NÃO TEM CACHE, ESPERA ATUALIZAR
            self.log("Sem cache. Pedindo dados ao vivo...")
            if LocationManager.NETWORK_PROVIDER in providers_list:
                self.log("Inscrito no provedor de REDE.")
                self.location_manager.requestLocationUpdates(
                    LocationManager.NETWORK_PROVIDER, 1000, 0.0, self.listener, Looper.getMainLooper())
            
            if LocationManager.GPS_PROVIDER in providers_list:
                self.log("Inscrito no provedor de GPS.")
                self.location_manager.requestLocationUpdates(
                    LocationManager.GPS_PROVIDER, 1000, 0.0, self.listener, Looper.getMainLooper())
                    
            self.log("Aguardando satélite (mexa o celular)...")

        except Exception as e:
            self.log(f"ERRO FATAL: {e}")
            self.parar_gps()

    def on_location_nativa(self, lat, lon):
        self.log(f"Coordenadas pegas! Lat:{lat:.3f} Lon:{lon:.3f}")
        self.parar_gps()
        Clock.schedule_once(lambda dt: self.processar_coordenadas(lat, lon), 0)

    def parar_gps(self):
        if self.location_manager and self.listener:
            self.location_manager.removeUpdates(self.listener)
        self.gps_ativo = False
        self.ids.btn_gps.disabled = False
        self.ids.btn_gps.text = "Testar Novamente"

    def processar_coordenadas(self, lat, lon):
        self.ids.btn_gps.text = "Sucesso!"
        self.ids.btn_gps.md_bg_color = "#4CAF50"
        self.log("Iniciando tradução na internet...")
        threading.Thread(target=self.traduzir_coordenada, args=(lat, lon)).start()

    def traduzir_coordenada(self, lat, lon):
        try:
            headers = {'User-Agent': 'VigiAA_PoC/1.0'}
            url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=18&addressdetails=1"
            res = requests.get(url, headers=headers).json()
            addr = res.get("address", {})
            self.atualizar_campos_gps(addr)
        except Exception as e:
            self.log(f"Erro traduzindo rua: {e}")

    @mainthread
    def atualizar_campos_gps(self, addr):
        self.log("Tradução concluída! Preenchendo tela.")
        self.ids.tf_bairro.text = addr.get("suburb", addr.get("neighbourhood", addr.get("district", "")))
        self.ids.tf_rua.text = addr.get("road", "")

class VigiAAPoCApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "LightBlue"
        Builder.load_string(KV)
        return FocusFormScreen()

if __name__ == "__main__":
    VigiAAPoCApp().run()
