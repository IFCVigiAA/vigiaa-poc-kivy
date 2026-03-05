from kivymd.app import MDApp
from kivy.lang import Builder
from kivymd.uix.screen import MDScreen
from kivymd.uix.snackbar import Snackbar
from kivy.clock import mainthread, Clock
from kivy.utils import platform
import requests
import threading

# --- A MÁGICA DO GPS NATIVO QUE FUNCIONOU ---
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
            self.callback(location.getLatitude(), location.getLongitude())

        @java_method('(Ljava/lang/String;)V')
        def onProviderDisabled(self, provider): pass

        @java_method('(Ljava/lang/String;)V')
        def onProviderEnabled(self, provider): pass

        @java_method('(Ljava/lang/String;ILandroid/os/Bundle;)V')
        def onStatusChanged(self, provider, status, extras): pass

# --- O VISUAL DO FORMULÁRIO DE DENGUE ---
KV = '''
<FocusFormScreen>:
    md_bg_color: 0.95, 0.95, 0.95, 1  # Fundo levemente cinza para destacar o formulário

    MDBoxLayout:
        orientation: "vertical"

        MDTopAppBar:
            title: "Registrar Foco - VigiAA"
            md_bg_color: "#1976D2" # Azul profissional
            specific_text_color: 1, 1, 1, 1
            elevation: 2

        ScrollView:
            MDBoxLayout:
                orientation: "vertical"
                padding: "20dp"
                spacing: "15dp"
                adaptive_height: True

                # SESSÃO 1: DADOS DO FOCO
                MDCard:
                    orientation: "vertical"
                    padding: "15dp"
                    spacing: "10dp"
                    adaptive_height: True
                    radius: [10, 10, 10, 10]
                    elevation: 1

                    MDLabel:
                        text: "Detalhes do Foco"
                        font_style: "H6"
                        theme_text_color: "Primary"

                    MDTextField:
                        id: tf_tipo
                        hint_text: "Tipo de Recipiente (ex: Pneu, Vaso, Caixa)"
                        icon_left: "delete-variant"

                    MDTextField:
                        id: tf_qtd
                        hint_text: "Quantidade Encontrada"
                        input_filter: "int"
                        icon_left: "counter"

                    MDTextField:
                        id: tf_obs
                        hint_text: "Observações Adicionais"
                        multiline: True
                        icon_left: "text-box-outline"

                # SESSÃO 2: LOCALIZAÇÃO
                MDCard:
                    orientation: "vertical"
                    padding: "15dp"
                    spacing: "10dp"
                    adaptive_height: True
                    radius: [10, 10, 10, 10]
                    elevation: 1

                    MDLabel:
                        text: "Endereço da Ocorrência"
                        font_style: "H6"
                        theme_text_color: "Primary"

                    MDRaisedButton:
                        id: btn_gps
                        text: "Capturar Localização Exata"
                        icon: "crosshairs-gps"
                        md_bg_color: "#FF9800" # Laranja chamativo
                        size_hint_x: 1
                        on_release: root.iniciar_gps()

                    MDLabel:
                        id: lbl_gps_status
                        text: "Toque no botão para preencher automaticamente."
                        theme_text_color: "Hint"
                        font_style: "Caption"
                        halign: "center"

                    MDTextField:
                        id: tf_rua
                        hint_text: "Rua"
                    
                    MDBoxLayout:
                        spacing: "10dp"
                        adaptive_height: True
                        MDTextField:
                            id: tf_numero
                            hint_text: "Número"
                            size_hint_x: 0.3
                        MDTextField:
                            id: tf_bairro
                            hint_text: "Bairro"
                            size_hint_x: 0.7

                    MDTextField:
                        id: tf_cidade
                        hint_text: "Cidade"

                # BOTÃO FINAL DE SALVAR
                MDRaisedButton:
                    text: "SALVAR REGISTRO"
                    icon: "content-save"
                    md_bg_color: "#4CAF50" # Verde sucesso
                    size_hint_x: 1
                    font_size: "18sp"
                    on_release: root.salvar_dados()
'''

class FocusFormScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.gps_ativo = False
        self.location_manager = None
        self.listener = None
        self.lat = ""
        self.lon = ""

    def iniciar_gps(self):
        if self.gps_ativo:
            return
            
        self.ids.btn_gps.text = "Acessando GPS..."
        self.ids.btn_gps.disabled = True
        
        if platform == 'android':
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.ACCESS_FINE_LOCATION, Permission.ACCESS_COARSE_LOCATION], self.gps_callback)
        else:
            self.mostrar_aviso("O GPS Nativo só funciona no celular.")
            self.ids.btn_gps.disabled = False
            self.ids.btn_gps.text = "Capturar Localização Exata"

    def gps_callback(self, permissions, results):
        if all(results):
            Clock.schedule_once(self.ligar_antena_nativa, 0)
        else:
            self.mostrar_aviso("Permissão de GPS negada.")
            self.ids.btn_gps.disabled = False
            self.ids.btn_gps.text = "Capturar Localização Exata"

    @mainthread
    def ligar_antena_nativa(self, dt):
        self.gps_ativo = True
        self.ids.lbl_gps_status.text = "Buscando sinal..."

        try:
            activity = PythonActivity.mActivity
            self.location_manager = activity.getSystemService(Context.LOCATION_SERVICE)
            self.listener = LocationListener(self.on_location_nativa)
            
            # TENTA O CACHE INSTANTÂNEO PRIMEIRO
            loc_net = self.location_manager.getLastKnownLocation(LocationManager.NETWORK_PROVIDER)
            if loc_net:
                self.on_location_nativa(loc_net.getLatitude(), loc_net.getLongitude())
                return
                
            loc_gps = self.location_manager.getLastKnownLocation(LocationManager.GPS_PROVIDER)
            if loc_gps:
                self.on_location_nativa(loc_gps.getLatitude(), loc_gps.getLongitude())
                return

            # SE NÃO TEM CACHE, ESPERA ATUALIZAR AO VIVO
            providers = self.location_manager.getProviders(True).toArray()
            providers_list = [p for p in providers]

            if LocationManager.NETWORK_PROVIDER in providers_list:
                self.location_manager.requestLocationUpdates(LocationManager.NETWORK_PROVIDER, 1000, 0.0, self.listener, Looper.getMainLooper())
            
            if LocationManager.GPS_PROVIDER in providers_list:
                self.location_manager.requestLocationUpdates(LocationManager.GPS_PROVIDER, 1000, 0.0, self.listener, Looper.getMainLooper())

        except Exception as e:
            self.mostrar_aviso("Falha ao ligar antena do celular.")
            self.parar_gps()

    def on_location_nativa(self, lat, lon):
        self.parar_gps()
        Clock.schedule_once(lambda dt: self.processar_coordenadas(lat, lon), 0)

    def parar_gps(self):
        if self.location_manager and self.listener:
            self.location_manager.removeUpdates(self.listener)
        self.gps_ativo = False

    @mainthread
    def processar_coordenadas(self, lat, lon):
        self.lat = lat
        self.lon = lon
        self.ids.btn_gps.text = "Localização Capturada!"
        self.ids.btn_gps.md_bg_color = "#4CAF50" # Verde
        self.ids.lbl_gps_status.text = "Traduzindo coordenadas na internet..."
        
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
            self.resetar_botao()

    @mainthread
    def atualizar_campos_gps(self, addr):
        self.ids.tf_cidade.text = addr.get("city", addr.get("town", addr.get("village", "")))
        self.ids.tf_bairro.text = addr.get("suburb", addr.get("neighbourhood", addr.get("district", "")))
        self.ids.tf_rua.text = addr.get("road", "")
        self.ids.lbl_gps_status.text = f"Lat: {self.lat:.5f} | Lon: {self.lon:.5f}"
        self.ids.btn_gps.disabled = False

    @mainthread
    def resetar_botao(self):
        self.ids.lbl_gps_status.text = "Preencha o restante manualmente se necessário."
        self.ids.btn_gps.disabled = False

    def salvar_dados(self):
        # Aqui ficará a lógica futura de enviar para o seu Django!
        tipo = self.ids.tf_tipo.text
        qtd = self.ids.tf_qtd.text
        
        if not tipo or not qtd:
            self.mostrar_aviso("Preencha o tipo e a quantidade do foco!")
            return
            
        self.mostrar_aviso(f"Sucesso! {qtd}x '{tipo}' prontos para envio ao banco de dados.")

    @mainthread
    def mostrar_aviso(self, texto):
        Snackbar(text=texto).open()

class VigiAAApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "Blue"
        Builder.load_string(KV)
        return FocusFormScreen()

if __name__ == "__main__":
    VigiAAApp().run()
