from kivymd.app import MDApp
from kivy.lang import Builder
from kivymd.uix.screen import MDScreen
from kivymd.uix.snackbar import Snackbar  # <--- CORRIGIDO AQUI
from kivy.clock import mainthread
from kivy.utils import platform
from plyer import gps
import requests
import threading

KV = '''
<FocusFormScreen>:
    md_bg_color: 1, 1, 1, 1

    MDBoxLayout:
        orientation: "vertical"

        MDTopAppBar:
            title: "Teste GPS Nativo"
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
                    text: "Ligar Antena GPS"
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
                    hint_text: "Município"

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
        self.gps_lat = ""
        self.gps_lon = ""

    def iniciar_gps(self):
        self.ids.btn_gps.text = "Pedindo permissão ao Android..."
        self.ids.btn_gps.disabled = True
        
        if platform == 'android':
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.ACCESS_FINE_LOCATION, Permission.ACCESS_COARSE_LOCATION], self.gps_callback)
        else:
            self.mostrar_aviso("O GPS Nativo só funciona no celular.")
            self.ids.btn_gps.text = "Ligar Antena GPS"
            self.ids.btn_gps.disabled = False

    def gps_callback(self, permissions, results):
        if all(results):
            try:
                gps.configure(on_location=self.on_location, on_status=self.on_status)
                gps.start(minTime=1000, minDistance=1)
                self.ids.lbl_gps_status.text = "Satélite conectado. Buscando coordenadas..."
            except Exception as e:
                self.mostrar_aviso(f"Erro no sensor: {e}")
        else:
            self.mostrar_aviso("Permissão negada.")
            self.ids.btn_gps.text = "Ligar Antena GPS"
            self.ids.btn_gps.disabled = False

    @mainthread
    def on_location(self, **kwargs):
        gps.stop() 
        self.gps_lat = kwargs.get('lat')
        self.gps_lon = kwargs.get('lon')
        
        self.ids.btn_gps.text = "Coordenada Capturada!"
        self.ids.btn_gps.icon = "check"
        self.ids.lbl_gps_status.text = f"Lat: {self.gps_lat:.5f} | Lon: {self.gps_lon:.5f}"
        
        threading.Thread(target=self.traduzir_coordenada, args=(self.gps_lat, self.gps_lon)).start()

    @mainthread
    def on_status(self, stype, status):
        pass

    def traduzir_coordenada(self, lat, lon):
        try:
            headers = {'User-Agent': 'VigiAA_PoC/1.0'}
            url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={lat}&lon={lon}&zoom=18&addressdetails=1"
            res = requests.get(url, headers=headers).json()
            addr = res.get("address", {})
            self.atualizar_campos_gps(addr)
        except:
            self.mostrar_aviso("Coordenada obtida, mas sem internet para traduzir a rua.")

    @mainthread
    def atualizar_campos_gps(self, addr):
        self.ids.tf_cidade.text = addr.get("city", addr.get("town", ""))
        self.ids.tf_rua.text = addr.get("road", "")
        self.ids.tf_cep.text = addr.get("postcode", "")
        self.ids.btn_gps.disabled = False

    @mainthread
    def mostrar_aviso(self, texto):
        # <--- CORRIGIDO AQUI PARA A VERSÃO 1.2.0 --->
        Snackbar(text=texto).open()

class VigiAAPoCApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "LightBlue"
        Builder.load_string(KV)
        return FocusFormScreen()

if __name__ == "__main__":
    VigiAAPoCApp().run()