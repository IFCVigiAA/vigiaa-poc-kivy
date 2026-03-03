[app]
title = VigiAA PoC
package.name = vigiaapoc
package.domain = org.vi
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 1.0

# Adicionado o 'pillow' para o KivyMD não travar o app
requirements = python3,kivy==2.3.0,kivymd==1.2.0,pillow,plyer,requests,urllib3,charset-normalizer,idna,certifi

# Permissões do Satélite
android.permissions = INTERNET, ACCESS_FINE_LOCATION, ACCESS_COARSE_LOCATION

android.api = 33
android.minapi = 21
android.archs = arm64-v8a, armeabi-v7a

# Comando que aceita as licenças do Google automaticamente
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
