import math
import os
import sys
import time
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import paho.mqtt.client as mqtt


# MQTT Broker Configuration
BROKER = "127.0.0.1"
PORT = 1883


def caminho_recurso(nome_arquivo):
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, nome_arquivo)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_dir, nome_arquivo)


ICONE_APP = caminho_recurso("icone.ico")


# Topics
TOPICS = {
    "casa/solar": "Irradiancia",
    "casa/led": ["on", "off"],
    "casa/ventilador": ["horario", "antihorario", "desligar"]
}


class CasaSimulador:
    def __init__(self, master=None):
        self.master = master
        self.master.title("Simulador da Casa do edder")
        self.aplicar_icone(self.master)
        self.master.configure(fg_color="#dfe7ef")
        self.master.protocol("WM_DELETE_WINDOW", self.fechar)

        self.estado_lampada = "Desligada"
        self.estado_ventilador = "Desligado"
        self.estado_solar = "0"
        self.hora_dia = 12.0
        self.angulo_ventilador = 0
        self.sentido_ventilador = 0
        self.status_atual = "Configure o broker MQTT"
        self.broker = BROKER
        self.porta = PORT
        self.client = None
        self.mostrar_mensagem_conectado = False
        self.atualizando_barra = False
        self.ultimo_envio_solar = 0
        self.irradiancia_automatica = tk.IntVar(value=1)

        self.widget1 = ctk.CTkFrame(master, fg_color="#dfe7ef", corner_radius=0)
        self.widget1.pack(fill="both", expand=True)

        self.cabecalho = ctk.CTkFrame(self.widget1, fg_color="#dfe7ef", width=620, height=38, corner_radius=0)
        self.cabecalho.pack(fill="x")
        self.cabecalho.pack_propagate(False)

        self.titulo = ctk.CTkLabel(
            self.cabecalho,
            text="🏠 CASA EDDER ⚡",
            text_color="#0f172a",
            font=("Calibri", 18, "bold")
        )
        self.titulo.place(relx=0.5, rely=0.5, anchor="center")

        self.botao_configuracao = ctk.CTkButton(
            self.cabecalho,
            text="⚙",
            command=self.abrir_configuracao_mqtt,
            width=34,
            height=28,
            fg_color="#ffffff",
            hover_color="#e2e8f0",
            text_color="#1f2937",
            border_color="#475569",
            border_width=2,
            corner_radius=7,
            font=("Segoe UI Symbol", 15, "bold")
        )
        self.botao_configuracao.place(x=535, y=5)

        self.botao_topicos = ctk.CTkButton(
            self.cabecalho,
            text="!",
            command=self.mostrar_topicos_mqtt,
            width=34,
            height=28,
            fg_color="#dbeafe",
            hover_color="#bfdbfe",
            text_color="#1d4ed8",
            border_color="#2563eb",
            border_width=2,
            corner_radius=7,
            font=("Calibri", 15, "bold")
        )
        self.botao_topicos.place(x=576, y=5)

        self.canvas = tk.Canvas(
            self.widget1,
            width=620,
            height=380,
            bg="#dfe7ef",
            highlightthickness=0
        )
        self.canvas.pack()

        self.area_tempo = ctk.CTkFrame(self.widget1, fg_color="#e8eef5", corner_radius=8)
        self.area_tempo.pack(fill="x", padx=12, pady=(8, 0))

        self.texto_hora = ctk.CTkLabel(
            self.area_tempo,
            text="Hora do dia: 12:00",
            text_color="#0f172a",
            font=("Calibri", 12, "bold")
        )
        self.texto_hora.pack(pady=(8, 2))

        self.barra_hora = ctk.CTkSlider(
            self.area_tempo,
            from_=0,
            to=24,
            orientation="horizontal",
            width=520,
            number_of_steps=240,
            fg_color="#cbd5e1",
            progress_color="#2563eb",
            button_color="#f8fafc",
            button_hover_color="#bfdbfe",
            command=self.mudar_hora
        )
        self.barra_hora.set(self.hora_dia)
        self.barra_hora.pack(pady=(0, 6))

        self.progresso_hora = ctk.CTkProgressBar(
            self.area_tempo,
            orientation="horizontal",
            width=520,
            height=8,
            fg_color="#cbd5e1",
            progress_color="#22c55e"
        )
        self.progresso_hora.set(self.hora_dia / 24)
        self.progresso_hora.pack(pady=(0, 8))

        self.check_auto = ctk.CTkCheckBox(
            self.area_tempo,
            text="Irradiancia automatica",
            variable=self.irradiancia_automatica,
            text_color="#1f2937",
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            border_color="#64748b",
            font=("Calibri", 11)
        )
        self.check_auto.pack(pady=(0, 10))

        self.desenhar_casa()
        self.atualizar_solar_pela_hora()
        self.animar_cena()
        self.master.after(200, self.abrir_configuracao_mqtt)

    def aplicar_icone(self, janela):
        if os.path.exists(ICONE_APP):
            try:
                janela.iconbitmap(ICONE_APP)
            except:
                pass

    def criar_cliente_mqtt(self):
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message

    def conectar_mqtt(self):
        if self.client is not None:
            try:
                self.client.loop_stop()
                self.client.disconnect()
            except:
                pass

        self.criar_cliente_mqtt()
        self.atualizar_status("Conectando: " + self.broker + ":" + str(self.porta))

        try:
            self.client.connect(self.broker, self.porta)
            self.client.loop_start()
        except Exception as erro:
            self.mostrar_mensagem_conectado = False
            self.atualizar_status("Falha: " + self.broker + ":" + str(self.porta))
            messagebox.showerror(
                "Erro",
                "Nao foi possivel conectar ao broker MQTT\n\n" + str(erro)
            )

    def mqtt_conectado(self):
        self.atualizar_status("Conectado ao broker")
        if self.mostrar_mensagem_conectado:
            self.mostrar_mensagem_conectado = False
            messagebox.showinfo("MQTT", "Conectado ao broker", parent=self.master)

    def mostrar_topicos_mqtt(self):
        mensagem = (
            "Topicos MQTT usados pela casa:\n\n"
            "casa/solar\n"
            "  Valor de irradiancia, normalmente de 0 a 1000.\n\n"
            "casa/led\n"
            "  Comandos aceitos: on, off.\n\n"
            "casa/ventilador\n"
            "  Comandos aceitos: horario, antihorario, desligar."
        )
        messagebox.showinfo("Topicos MQTT", mensagem, parent=self.master)

    def abrir_configuracao_mqtt(self):
        janela = tk.Toplevel(self.master)
        janela.withdraw()
        janela.title("Configuracao MQTT")
        self.aplicar_icone(janela)
        janela.configure(bg="#dfe7ef")
        janela.resizable(False, False)
        janela.transient(self.master)
        janela.grab_set()

        broker_var = tk.StringVar(value=self.broker)
        porta_var = tk.StringVar(value=str(self.porta))

        tk.Label(
            janela,
            text="Broker",
            bg="#dfe7ef",
            fg="#1f2937",
            font=("Calibri", "10", "bold")
        ).grid(row=0, column=0, padx=12, pady=(12, 4), sticky="w")

        entrada_broker = tk.Entry(janela, textvariable=broker_var, width=24)
        entrada_broker.grid(row=0, column=1, padx=12, pady=(12, 4), sticky="ew")

        tk.Label(
            janela,
            text="Porta",
            bg="#dfe7ef",
            fg="#1f2937",
            font=("Calibri", "10", "bold")
        ).grid(row=1, column=0, padx=12, pady=4, sticky="w")

        entrada_porta = tk.Entry(janela, textvariable=porta_var, width=24)
        entrada_porta.grid(row=1, column=1, padx=12, pady=4, sticky="ew")

        botoes = tk.Frame(janela, bg="#dfe7ef")
        botoes.grid(row=2, column=0, columnspan=2, padx=12, pady=12, sticky="e")

        def salvar():
            broker = broker_var.get().strip()

            if broker == "":
                messagebox.showerror("Erro", "Informe o broker MQTT.", parent=janela)
                return

            try:
                porta = int(porta_var.get())
            except ValueError:
                messagebox.showerror("Erro", "A porta deve ser um numero.", parent=janela)
                return

            if porta < 1 or porta > 65535:
                messagebox.showerror("Erro", "A porta deve estar entre 1 e 65535.", parent=janela)
                return

            self.broker = broker
            self.porta = porta
            self.mostrar_mensagem_conectado = True
            janela.destroy()
            self.conectar_mqtt()

        tk.Button(
            botoes,
            text="Cancelar",
            command=janela.destroy,
            bg="#f8fafc",
            fg="#1f2937",
            width=10
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            botoes,
            text="Salvar",
            command=salvar,
            bg="#2563eb",
            fg="#ffffff",
            activebackground="#1d4ed8",
            width=10
        ).pack(side="left")

        janela.update_idletasks()
        largura = janela.winfo_width()
        altura = janela.winfo_height()
        x = self.master.winfo_x() + (self.master.winfo_width() - largura) // 2
        y = self.master.winfo_y() + (self.master.winfo_height() - altura) // 2
        janela.geometry("+{}+{}".format(x, y))
        janela.deiconify()
        janela.lift()
        janela.focus_force()

        entrada_broker.focus_set()

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            client.subscribe("casa/led")
            client.subscribe("casa/ventilador")
            client.subscribe("casa/solar")
            self.master.after(0, self.mqtt_conectado)
        else:
            self.mostrar_mensagem_conectado = False
            self.master.after(0, self.atualizar_status, "Falha na conexao")

    def on_message(self, client, userdata, message):
        topico = message.topic
        mensagem = message.payload.decode("utf-8")
        self.master.after(0, self.tratar_mensagem, topico, mensagem)

    def tratar_mensagem(self, topico, mensagem):
        if topico == "casa/led":
            if mensagem == "on":
                self.estado_lampada = "Ligada"
            elif mensagem == "off":
                self.estado_lampada = "Desligada"

        elif topico == "casa/ventilador":
            if mensagem == "horario":
                self.estado_ventilador = "Girando horario"
                self.sentido_ventilador = 1
            elif mensagem == "antihorario":
                self.estado_ventilador = "Girando anti-horario"
                self.sentido_ventilador = -1
            elif mensagem == "desligar":
                self.estado_ventilador = "Desligado"
                self.sentido_ventilador = 0

        elif topico == "casa/solar":
            self.estado_solar = mensagem

        self.desenhar_casa()
        self.atualizar_status(topico + " -> " + mensagem)

    def limitar(self, valor, minimo, maximo):
        return max(minimo, min(valor, maximo))

    def suavizar(self, minimo, maximo, valor):
        valor = self.limitar((valor - minimo) / (maximo - minimo), 0, 1)
        return valor * valor * (3 - 2 * valor)

    def misturar_cor(self, cor1, cor2, quantidade):
        quantidade = self.limitar(quantidade, 0, 1)
        r1 = int(cor1[1:3], 16)
        g1 = int(cor1[3:5], 16)
        b1 = int(cor1[5:7], 16)
        r2 = int(cor2[1:3], 16)
        g2 = int(cor2[3:5], 16)
        b2 = int(cor2[5:7], 16)
        r = int(r1 + (r2 - r1) * quantidade)
        g = int(g1 + (g2 - g1) * quantidade)
        b = int(b1 + (b2 - b1) * quantidade)
        return "#" + format(r, "02x") + format(g, "02x") + format(b, "02x")

    def fator_dia(self):
        amanhecer = self.suavizar(5, 7, self.hora_dia)
        anoitecer = 1 - self.suavizar(17, 19, self.hora_dia)
        return min(amanhecer, anoitecer)

    def cor_do_ceu(self):
        noite = "#172554"
        amanhecer = "#fb923c"
        dia = "#7dd3fc"

        if 5 <= self.hora_dia < 6:
            return self.misturar_cor(noite, amanhecer, self.suavizar(5, 6, self.hora_dia))
        if 6 <= self.hora_dia < 8:
            return self.misturar_cor(amanhecer, dia, self.suavizar(6, 8, self.hora_dia))
        if 16 <= self.hora_dia < 18:
            return self.misturar_cor(dia, amanhecer, self.suavizar(16, 18, self.hora_dia))
        if 18 <= self.hora_dia < 19:
            return self.misturar_cor(amanhecer, noite, self.suavizar(18, 19, self.hora_dia))

        return self.misturar_cor(noite, dia, self.fator_dia())

    def desenhar_casa(self):
        self.canvas.delete("all")

        lampada_ligada = self.estado_lampada == "Ligada"
        luz = "#fff4a3" if lampada_ligada else "#f1f5f9"
        lampada = "#facc15" if lampada_ligada else "#94a3b8"
        dia = self.fator_dia()
        parede = self.misturar_cor("#b8c2d1", "#f8fafc", dia)
        fundo = self.misturar_cor("#0f172a", "#dfe7ef", dia)

        if lampada_ligada:
            parede = self.misturar_cor(parede, "#fff7d6", 0.35)

        self.canvas.configure(bg=fundo)

        self.canvas.create_rectangle(30, 45, 590, 330, fill=parede, outline="#94a3b8", width=2)

        self.canvas.create_polygon(
            18, 45,
            310, 4,
            602, 45,
            590, 53,
            310, 14,
            30, 53,
            fill="#475569",
            outline="#334155",
            width=2
        )
        self.canvas.create_polygon(
            30, 45,
            310, 8,
            590, 45,
            310, 39,
            fill="#64748b",
            outline="#475569",
            width=2
        )
        self.canvas.create_line(30, 53, 590, 53, fill="#334155", width=3)

        self.canvas.create_rectangle(30, 330, 590, 380, fill="#cbd5e1", outline="#94a3b8")
        self.canvas.create_rectangle(30, 330, 590, 340, fill="#94a3b8", outline="")
        self.canvas.create_polygon(
            30, 340,
            590, 340,
            570, 380,
            50, 380,
            fill="#d8e0ea",
            outline=""
        )
        self.canvas.create_line(52, 360, 568, 360, fill="#c3ceda", width=1)
        self.canvas.create_line(70, 378, 550, 378, fill="#b8c5d2", width=1)
        self.canvas.create_rectangle(78, 205, 148, 330, fill="#b08968", outline="#7f5539", width=2)
        self.canvas.create_oval(132, 262, 142, 272, fill="#facc15", outline="#92400e")

        self.desenhar_janela()
        self.desenhar_lampada(luz, lampada, lampada_ligada)
        self.desenhar_ventilador()
        self.desenhar_painel()

    def desenhar_janela(self):
        valor = int(self.estado_solar) if self.estado_solar.isdigit() else 0
        noite = self.hora_dia < 6 or self.hora_dia > 18
        ceu = self.cor_do_ceu()
        sol = "#facc15" if valor > 650 else "#fde68a"
        x1 = 64
        y1 = 82
        x2 = 218
        y2 = 174
        meio_x = (x1 + x2) / 2
        meio_y = (y1 + y2) / 2

        self.canvas.create_rectangle(x1 - 5, y1 - 5, x2 + 5, y2 + 5, fill="#1d4ed8", outline="#1e40af")
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=ceu, outline="")

        if noite:
            hora_noite = self.hora_dia
            if hora_noite < 6:
                hora_noite = hora_noite + 24

            progresso = (hora_noite - 18) / 12
            x = 88 + progresso * 106
            y = 146 - math.sin(progresso * math.pi) * 43
            self.canvas.create_oval(x - 15, y - 15, x + 15, y + 15, fill="#e5e7eb", outline="#94a3b8")
            self.canvas.create_oval(x - 5, y - 19, x + 22, y + 11, fill=ceu, outline=ceu)
            texto = "Lua - irradiancia: " + self.estado_solar
        else:
            progresso = (self.hora_dia - 6) / 12
            x = 88 + progresso * 106
            y = 146 - math.sin(progresso * math.pi) * 43
            self.canvas.create_oval(x - 15, y - 15, x + 15, y + 15, fill=sol, outline="#f59e0b")
            texto = "Sol - irradiancia: " + self.estado_solar

        self.canvas.create_rectangle(x1, y1, x2, y2, outline="#2563eb", width=3)
        self.canvas.create_line(meio_x, y1, meio_x, y2, fill="#2563eb", width=3)
        self.canvas.create_line(x1, meio_y, x2, meio_y, fill="#2563eb", width=3)
        self.canvas.create_rectangle(x1 + 8, y1 + 8, x2 - 8, y2 - 8, outline="#93c5fd", width=1)
        self.canvas.create_rectangle(
            61, 181,
            221, 206,
            fill="#eef2f7",
            outline="#94a3b8",
            width=1
        )
        self.canvas.create_text(141, 194, text=texto, fill="#1f2937", font=("Calibri", "10", "bold"))
    def desenhar_lampada(self, luz, lampada, lampada_ligada):
        cx = 310

        fio_topo = 40
        soquete_topo = 78
        soquete_base = 96
        rosca_topo = 96
        rosca_base = 112
        vidro_topo = 108
        vidro_base = 164

        if lampada_ligada:
            self.canvas.create_oval(
                cx - 58, soquete_topo - 14,
                cx + 58, vidro_base + 26,
                fill="#fff1a6",
                outline=""
            )
            self.canvas.create_oval(
                cx - 43, rosca_topo + 2,
                cx + 43, vidro_base + 12,
                fill="#fff6bd",
                outline=""
            )
            self.canvas.create_oval(
                cx - 30, vidro_topo + 6,
                cx + 30, vidro_base + 6,
                fill="#fff9dc",
                outline=""
            )
            self.canvas.create_polygon(
                cx - 17, vidro_base - 7,
                cx + 17, vidro_base - 7,
                cx + 48, 330,
                cx - 48, 330,
                fill="#fff5c8",
                outline=""
            )
            self.canvas.create_polygon(
                cx - 8, vidro_base,
                cx + 8, vidro_base,
                cx + 24, 330,
                cx - 24, 330,
                fill="#fffbe8",
                outline=""
            )
            self.canvas.create_oval(
                cx - 48, 323,
                cx + 48, 337,
                fill="#fff8dc",
                outline=""
            )

        self.canvas.create_line(
            cx, fio_topo,
            cx, soquete_topo,
            fill="#1f2937",
            width=2
        )

        self.canvas.create_rectangle(
            cx - 15, soquete_topo,
            cx + 15, soquete_base,
            fill="#475569",
            outline="#1f2937",
            width=2
        )

        self.canvas.create_rectangle(
            cx - 12, rosca_topo,
            cx + 12, rosca_base,
            fill="#64748b",
            outline="#1f2937",
            width=2
        )

        for y in range(rosca_topo + 4, rosca_base, 4):
            self.canvas.create_line(
                cx - 11, y,
                cx + 11, y,
                fill="#cbd5e1",
                width=1
            )

        cor_vidro = "#fff1a8" if lampada_ligada else "#dbeafe"
        brilho_vidro = "#ffffff" if lampada_ligada else "#f8fafc"

        self.canvas.create_polygon(
            cx - 11, vidro_topo,
            cx - 24, vidro_topo + 10,
            cx - 30, vidro_topo + 32,
            cx - 25, vidro_topo + 49,
            cx - 12, vidro_base,
            cx, vidro_base + 5,
            cx + 12, vidro_base,
            cx + 25, vidro_topo + 49,
            cx + 30, vidro_topo + 32,
            cx + 24, vidro_topo + 10,
            cx + 11, vidro_topo,
            fill=cor_vidro,
            outline="#1f2937",
            width=2,
            smooth=True
        )

        self.canvas.create_oval(
            cx - 17, vidro_topo + 15,
            cx - 9, vidro_topo + 35,
            fill=brilho_vidro,
            outline=""
        )

        cor_filamento = "#ff8c00" if lampada_ligada else "#6b7280"

        self.canvas.create_line(
            cx - 9, vidro_topo + 43,
            cx - 9, vidro_topo + 33,
            fill=cor_filamento,
            width=2
        )
        self.canvas.create_line(
            cx + 9, vidro_topo + 43,
            cx + 9, vidro_topo + 33,
            fill=cor_filamento,
            width=2
        )
        self.canvas.create_line(
            cx - 9, vidro_topo + 33,
            cx - 5, vidro_topo + 29,
            cx, vidro_topo + 34,
            cx + 5, vidro_topo + 29,
            cx + 9, vidro_topo + 33,
            fill=cor_filamento,
            width=2,
            smooth=True
        )

        self.canvas.create_rectangle(
            cx - 70, 210,
            cx + 42, 234,
            fill="#fff7d6" if lampada_ligada else "#eaf2fb",
            outline="#c9a64a" if lampada_ligada else "#8aa7c7",
            width=1
        )
        self.canvas.create_text(
            cx - 14,
            222,
            text="Lampada: " + self.estado_lampada,
            fill="#1f2937",
            font=("Calibri", 10, "bold")
        )
    
    def desenhar_ventilador(self):
        cx = 455
        cy = 155
        raio = 62

        self.canvas.create_line(cx, 92, cx, cy, fill="#334155", width=4)
        self.canvas.create_oval(cx - 18, cy - 18, cx + 18, cy + 18, fill="#475569", outline="#1e293b", width=2)

        for i in range(4):
            angulo = math.radians(self.angulo_ventilador + (i * 90))
            ponta_x = cx + math.cos(angulo) * raio
            ponta_y = cy + math.sin(angulo) * raio
            lado_x = cx + math.cos(angulo + 0.45) * 22
            lado_y = cy + math.sin(angulo + 0.45) * 22
            self.canvas.create_polygon(cx, cy, ponta_x, ponta_y, lado_x, lado_y, fill="#38bdf8", outline="#0369a1")

        self.canvas.create_oval(cx - 8, cy - 8, cx + 8, cy + 8, fill="#e2e8f0", outline="#334155")
        self.canvas.create_rectangle(
            cx - 88, 222,
            cx + 88, 248,
            fill="#eef2f7",
            outline="#94a3b8",
            width=1
        )
        self.canvas.create_text(cx, 235, text="Ventilador: " + self.estado_ventilador, fill="#1f2937", font=("Calibri", "10", "bold"))

    def desenhar_painel(self):
        self.canvas.create_rectangle(355, 265, 565, 350, fill="#f8fafc", outline="#94a3b8", width=2)
        self.canvas.create_text(460, 288, text="Ultimo comando", fill="#475569", font=("Calibri", "11", "bold"))
        self.status_texto = self.canvas.create_text(460, 320, text=self.status_atual, fill="#0f172a", font=("Calibri", "10"))

    def atualizar_status(self, texto):
        self.status_atual = texto
        if hasattr(self, "status_texto"):
            self.canvas.itemconfig(self.status_texto, text=texto)

    def animar_cena(self):
        mudou = False

        if self.irradiancia_automatica.get() == 1:
            self.hora_dia = self.hora_dia + 0.00075
            if self.hora_dia > 24:
                self.hora_dia = 0

            self.atualizar_solar_pela_hora(redesenhar=False)
            mudou = True

        if self.sentido_ventilador != 0:
            self.angulo_ventilador = self.angulo_ventilador + (self.sentido_ventilador * 12)
            mudou = True

        if mudou:
            self.desenhar_casa()

        self.master.after(40, self.animar_cena)

    def mudar_hora(self, valor):
        if self.atualizando_barra:
            return

        self.hora_dia = float(valor)
        self.atualizar_solar_pela_hora()

    def atualizar_solar_pela_hora(self, redesenhar=True):
        if 6 <= self.hora_dia <= 18:
            fator = math.sin((self.hora_dia - 6) / 12 * math.pi)
            valor = int(fator * 1000)
        else:
            valor = 0

        self.estado_solar = str(valor)
        hora = int(self.hora_dia)
        minuto = int((self.hora_dia - hora) * 60)

        self.texto_hora.configure(text="Hora do dia: " + str(hora).zfill(2) + ":" + str(minuto).zfill(2))
        self.progresso_hora.set(self.hora_dia / 24)

        self.atualizando_barra = True
        self.barra_hora.set(round(self.hora_dia, 1))
        self.atualizando_barra = False

        agora = time.monotonic()
        if agora - self.ultimo_envio_solar > 0.5:
            if self.client is not None:
                try:
                    self.client.publish("casa/solar", self.estado_solar)
                except:
                    pass
            self.ultimo_envio_solar = agora

        if redesenhar:
            self.desenhar_casa()

    def fechar(self):
        if self.client is not None:
            try:
                self.client.loop_stop()
                self.client.disconnect()
            except:
                pass
        self.master.destroy()


ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

root = ctk.CTk()
CasaSimulador(root)
root.geometry("640x560")
root.mainloop()