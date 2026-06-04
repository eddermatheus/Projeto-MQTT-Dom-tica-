import tkinter as tk
import time
from paho.mqtt.client import Client

# ---------------- MQTT CONFIG ----------------
broker = "broker.hivemq.com"
porta = 1883
##usuario = "admin"
##senha = "DEEUFPE"

cliente = Client()
##cliente.username_pw_set(usuario, senha)

cliente.connect(broker, porta)
cliente.loop_start()

# ---------------- TKINTER ----------------
janela = tk.Tk()
janela.title("Painel Casa IoT do Edder")
janela.geometry("400x350")

# 🌞 IRRADIÂNCIA (MONITOR)
irradiancia_var = tk.StringVar()
irradiancia_var.set("0")
tk.Label(janela,text= "🏠Sisteminha de domótica⚡", font=("Arial",14, "bold"), fg ="darkblue").pack(pady=15)
tk.Label(janela, text="☀️ Irradiância Solar:", font = ("Arial",18,"bold")).pack()
tk.Label(janela, textvariable=irradiancia_var, font=("Arial", 18,"bold")).pack()

# ---------------- MQTT RECEBER DADOS ----------------
def on_message(client, userdata, msg):
    topico = msg.topic
    mensagem = msg.payload.decode()

    print(topico, mensagem)

    if topico == "casa/solar":
        irradiancia_var.set(mensagem)

cliente.on_message = on_message
cliente.subscribe("casa/solar")

# ---------------- FUNÇÕES DOS BOTÕES ----------------
def led_on():
    cliente.publish("casa/led", "on")

def led_off():
    cliente.publish("casa/led", "off")

def fan_horario():
    cliente.publish("casa/ventilador", "horario")

def fan_antihorario():
    cliente.publish("casa/ventilador", "antihorario")

def fan_off():
    cliente.publish("casa/ventilador", "desligar")

# ---------------- BOTÕES ----------------
tk.Label(janela, text="\n💡 LED", font = ("Arial",12,"bold")).pack()
tk.Button(janela, text="Ligar", command=led_on).pack()
tk.Button(janela, text="Desligar", command=led_off).pack()

tk.Label(janela, text="\n🌀 Ventilador", font = ("Arial",12,"bold")).pack()
tk.Button(janela, text="Horário", command=fan_horario).pack()
tk.Button(janela, text="Anti-horário", command=fan_antihorario).pack()
tk.Button(janela, text="Desligar", command=fan_off).pack()

# ---------------- FINAL ----------------
janela.mainloop()

cliente.loop_stop()
cliente.disconnect()