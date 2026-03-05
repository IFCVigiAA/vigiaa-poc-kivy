from kivymd.app import MDApp
from kivy.lang import Builder
from kivymd.uix.screen import MDScreen
from kivymd.uix.snackbar import Snackbar
from kivy.clock import mainthread, Clock
from kivy.utils import platform
import requests
import threading

# --- O MOTOR DO GPS (QUE JÁ VIMOS QUE FUNCIONA) ---
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

# --- O VISUAL FIEL AO SEU PROTÓTIPO ---
KV = '''
<FocusFormScreen>:
    md_bg_color: 1, 1, 1, 1  # Fundo totalmente branco

    MDBoxLayout:
        orientation: "vertical"

        # BARRA SUPERIOR BRANCA
        MDTopAppBar:
            title: "Focos de mosquitos"
            md_bg_color: 1, 1, 1, 1
            specific_text_color: 0, 0, 0, 1
            elevation: 0
            left_action_items: [["chevron-left", lambda x: root.voltar()]]

        ScrollView:
            MDBoxLayout:
                orientation: "vertical"
                padding: "20dp"
                spacing: "20dp"
                adaptive_height: True

                # BOTÃO DO GPS
                MDRaisedButton:
                    id: btn_gps
                    text: "Capturar localização pelo GPS"
                    icon: "map-marker"
                    md_bg_color: "#39BFEF" # Azul ciano do protótipo
                    text_color: 1, 1, 1, 1
                    size_hint_x: 0.9
                    pos_hint: {"center_x": .5}
                    elevation: 0
                    on_release: root.iniciar_gps()

                # AVISO OBRIGATÓRIO
                MDLabel:
                    text: "Campos marcos com [color=#FF0000]*[/color] são obrigatórios"
                    markup: True
                    font_style: "Caption"
                    theme_text_color: "Custom"
                    text_color: 0.3, 0.3, 0.3, 1

                # FORMULÁRIO (Lado a Lado)
                # CEP
                MDBoxLayout:
                    adaptive_height: True
                    MDLabel:
                        text: "CEP"
                        bold: True
                        size_hint_x: 0.35
                        font_style: "Body2"
                    MDTextField:
                        id: tf_cep
                        hint_text: "Digite o CEP"
                        size_hint_x: 0.65
                
                # MUNICÍPIO
                MDBoxLayout:
                    adaptive_height: True
                    MDLabel:
                        text: "MUNICÍPIO[color=#FF0000]*[/color]"
                        markup: True
                        bold: True
                        size_hint_x: 0.35
                        font_style: "Body2"
                    MDTextField:
                        id: tf_cidade
                        hint_text: "Selecione a cidade"
                        icon_right: "chevron-down"
                        size_hint_x: 0.65

                # BAIRRO
                MDBoxLayout:
                    adaptive_height: True
                    MDLabel:
                        text: "BAIRRO[color=#FF0000]*[/color]"
                        markup: True
                        bold: True
                        size_hint_x: 0.35
                        font_style: "Body2"
                    MDTextField:
                        id: tf_bairro
                        hint_text: "Selecione o bairro"
                        icon_right: "chevron-down"
                        size_hint_x: 0.65

                # RUA
                MDBoxLayout:
                    adaptive_height: True
                    MDLabel:
                        text: "RUA[color=#FF0000]*[/color]"
                        markup: True
                        bold: True
                        size_hint_x: 0.35
                        font_style: "Body2"
                    MDTextField:
                        id: tf_rua
                        hint_text: "Digite o nome da rua"
                        icon_right: "magnify"
                        size_hint_x: 0.65

                # NÚMERO
                MDBoxLayout:
                    adaptive_height: True
                    MDLabel:
                        text: "NÚMERO[color=#FF0000]*[/color]"
                        markup: True
                        bold: True
                        size_hint_x: 0.35
                        font_style: "Body2"
                    MDTextField:
                        id: tf_numero
                        hint_text: "Digite o número"
                        input_filter: "int"
                        size_hint_x: 0.65

                # DESCRIÇÃO
                MDBoxLayout:
                    adaptive_height: True
                    MDLabel:
                        text: "DESCRIÇÃO"
                        bold: True
                        size_hint_x: 0.35
                        font_style: "Body2"
                        pos_hint: {"top": 1}
                    MDTextField:
                        id: tf_desc
                        hint_text: "Descreva a situação do local.\\nObs: não se identifique de nenhuma forma"
                        multiline: True
                        size_hint_x: 0.65

                # SESSÃO IMAGENS
                MDLabel:
                    text: "IMAGENS"
                    bold: True
                    font_style: "Body2"
                    padding_y: "10dp"

                MDBoxLayout:
                    orientation: "horizontal"
                    spacing: "15dp"
                    adaptive_height: True
                    
                    # Botão quadrado cinza de Imagem
                    MDRaisedButton:
                        text: "+"
                        font_size: "32sp"
                        md_bg_color: 0.85, 0.85, 0.85, 1
                        text_color: 0.3, 0.3, 0.3, 1
                        elevation: 0
                        size_hint: None, None
                        size: "80dp", "80dp"
                        
                    MDLabel:
                        text: "Adicionar imagem"
                        theme_text_color: "Hint"

                # Um espaço extra para o botão de Cadastrar não ficar colado
                MDBoxLayout:
                    size_hint_y: None
                    height: "40dp"

        # BOTÃO FIXO NO RODAPÉ
        MDBoxLayout:
            padding: ["20dp", "10dp", "20dp", "20dp"]
            adaptive_height: True
            MDRaisedButton:
                text: "CADASTRAR"
                md_bg_color: "#39BFEF"
                text_color: 1, 1, 1, 1
                size_hint_x: 1
                font_size: "16sp"
                elevation: 0
                padding: "15dp"
                on_release: root.cadastrar()
'''

class FocusFormScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.gps_ativo = False
        self.location_manager = None
        self.listener = None

    def voltar(self):
        self.mostrar_aviso("Voltando para tela inicial...")

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
            self.ids.btn_gps.text = "Capturar localização pelo GPS"

    def gps_callback(self, permissions, results):
        if all(results):
            Clock.schedule_once(self.ligar_antena_nativa, 0)
        else:
            self.mostrar_aviso("Permissão de GPS negada.")
            self.ids.btn_gps.disabled = False
            self.ids.btn_gps.text = "Capturar localização pelo GPS"

    @mainthread
    def ligar_antena_nativa(self, dt):
        self.gps_ativo = True
        self.ids.btn_gps.text = "Buscando sinal..."

        try:
            activity = PythonActivity.mActivity
            self.location_manager = activity.getSystemService(Context.LOCATION_SERVICE)
            self.listener = LocationListener(self.on_location_nativa)
            
            # Cache Rápido
            loc_net = self.location_manager.getLastKnownLocation(LocationManager.NETWORK_PROVIDER)
            if loc_net:
                self.on_location_nativa(loc_net.getLatitude(), loc_net.getLongitude())
                return
                
            loc_gps = self.location_manager.getLastKnownLocation(LocationManager.GPS_PROVIDER)
            if loc_gps:
                self.on_location_nativa(loc_gps.getLatitude(), loc_gps.getLongitude())
                return

            # Busca ao vivo
            providers = self.location_manager.getProviders(True).toArray()
            providers_list = [p for p in providers]

            if LocationManager.NETWORK_PROVIDER in providers_list:
                self.location_manager.requestLocationUpdates(LocationManager.NETWORK_PROVIDER, 1000, 0.0, self.listener, Looper.getMainLooper())
            
            if LocationManager.GPS_PROVIDER in providers_list:
                self.location_manager.requestLocationUpdates(LocationManager.GPS_PROVIDER, 1000, 0.0, self.listener, Looper.getMainLooper())

        except Exception as e:
            self.mostrar_aviso("Falha ao ligar antena.")
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
        self.ids.btn_gps.text = "Traduzindo Endereço..."
        threading.Thread(target=self.traduzir_coordenada, args=(lat, lon)).start()

    def traduzir_coordenada(self, lat, lon):
        try:
            headers = {'User-Agent': 'VigiAA_PoC/1.0'}
            url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=18&addressdetails=1"
            res = requests.get(url, headers=headers).json()
            addr = res.get("address", {})
            self.atualizar_campos_gps(addr)
        except:
            self.mostrar_aviso("Sem internet para traduzir.")
            self.resetar_botao()

    @mainthread
    def atualizar_campos_gps(self, addr):
        # A nova "rede de segurança" para achar o nome do município e do bairro
        cidade = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("municipality") or ""
        bairro = addr.get("suburb") or addr.get("neighbourhood") or addr.get("city_district") or addr.get("district") or addr.get("quarter") or addr.get("borough") or ""
        rua = addr.get("road") or addr.get("street") or ""
        cep = addr.get("postcode", "")

        self.ids.tf_cidade.text = cidade
        self.ids.tf_bairro.text = bairro
        self.ids.tf_rua.text = rua
        self.ids.tf_cep.text = cep
        
        self.ids.btn_gps.text = "Localização Preenchida!"
        self.ids.btn_gps.icon = "check"
        self.ids.btn_gps.disabled = False

    @mainthread
    def resetar_botao(self):
        self.ids.btn_gps.text = "Capturar localização pelo GPS"
        self.ids.btn_gps.disabled = False

    def cadastrar(self):
        rua = self.ids.tf_rua.text
        if not rua:
            self.mostrar_aviso("Preencha os campos obrigatórios primeiro!")
            return
        self.mostrar_aviso("Cadastrando foco no banco de dados...")

    @mainthread
    def mostrar_aviso(self, texto):
        Snackbar(text=texto).open()

class VigiAAApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "LightBlue"
        Builder.load_string(KV)
        return FocusFormScreen()

if __name__ == "__main__":
    VigiAAApp().run()
