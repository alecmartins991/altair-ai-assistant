"""Desktop controls for the ChatGPT plan and a separate visual companion."""
import threading
import webbrowser
import math
import time

from PyQt5.QtCore import Qt, QTimer, QRectF, QPointF, QBuffer, QIODevice
from PyQt5.QtGui import QPainter, QColor, QPen, QBrush, QRadialGradient, QPolygonF
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, QComboBox,
                             QMessageBox, QCheckBox, QFileDialog, QWidget, QLineEdit, QHBoxLayout, QPlainTextEdit, QApplication, QDialogButtonBox)
from pathlib import Path

from altair.core.chatgpt_plan import ChatGPTSession, PlanError


def _background(parent, title, function):
    class Busy(QDialog):
        def reject(self):
            pass

    dialog = Busy(parent)
    dialog.setWindowTitle(title)
    dialog.setWindowFlags(Qt.Dialog | Qt.CustomizeWindowHint | Qt.WindowTitleHint)
    QVBoxLayout(dialog).addWidget(QLabel("Aguarde a operação. Conclua o login no navegador, se solicitado."))
    result = {}

    def work():
        try:
            result["value"] = function()
        except Exception as exc:
            result["error"] = str(exc) if isinstance(exc, (PlanError, PermissionError)) else (
                "Não foi possível concluir. Verifique a rede, dependências e autorização."
            )
        finally:
            result["done"] = True

    timer = QTimer(dialog)
    timer.timeout.connect(lambda: dialog.accept() if result.get("done") else None)
    threading.Thread(target=work, daemon=True).start()
    timer.start(100)
    dialog.exec_()
    timer.stop()
    if "error" in result:
        raise PlanError(result["error"])
    return result.get("value")


def configure_chatgpt(parent, initial):
    session = ChatGPTSession()
    dialog = QDialog(parent)
    dialog.setWindowTitle("ChatGPT — uso do plano")
    dialog.resize(480, 360)
    layout = QVBoxLayout(dialog)
    status = QLabel()
    status.setWordWrap(True)
    layout.addWidget(status)
    note = QLabel("Não é necessário criar API Key. Esta conexão não acessa chats, memória ou voz do ChatGPT oficial. Desative o uso de créditos extras nas configurações da sua conta antes de continuar.")
    note.setWordWrap(True)
    layout.addWidget(note)
    usage = QPushButton("Abrir limites e créditos no ChatGPT")
    usage.clicked.connect(lambda: webbrowser.open("https://chatgpt.com/settings/usage"))
    layout.addWidget(usage)
    consent = QCheckBox("Conferi que o uso de créditos extras está desativado.")
    layout.addWidget(consent)
    login = QPushButton("Continue with ChatGPT")
    layout.addWidget(login)
    logout = QPushButton("Desconectar")
    layout.addWidget(logout)
    refresh = QPushButton("Consultar modelos da minha conta")
    layout.addWidget(refresh)
    main, router = QComboBox(), QComboBox()
    layout.addWidget(QLabel("Modelo principal"))
    layout.addWidget(main)
    layout.addWidget(QLabel("Modelo para interpretar comandos"))
    layout.addWidget(router)
    apply = QPushButton("Usar plano ChatGPT no Altair")
    layout.addWidget(apply)
    memory = QCheckBox("Guardar contexto e últimas conversas neste computador (opcional)")
    layout.addWidget(memory)
    import_context = QPushButton("Importar contexto de projeto (.txt ou .md)")
    clear_memory = QPushButton("Apagar memória local desta conta")
    layout.addWidget(import_context)
    layout.addWidget(clear_memory)
    result = {}

    def change_memory(checked):
        try:
            data = session.memory()
            data["enabled"] = bool(checked)
            session.save_memory(data)
        except Exception:
            QMessageBox.warning(dialog, "Memória", "Não foi possível salvar a preferência.")
        sync()

    def import_file():
        path, _ = QFileDialog.getOpenFileName(dialog, "Escolha um resumo que deseja compartilhar", "", "Texto (*.txt *.md)")
        if not path:
            return
        try:
            with Path(path).open("r", encoding="utf-8-sig") as stream:
                content = stream.read(12001)
            if len(content) > 12000:
                QMessageBox.warning(dialog, "Memória", "Use um resumo de até 12.000 caracteres.")
                return
            if QMessageBox.question(dialog, "Memória", "Salvar este contexto e enviá-lo ao modelo nas próximas conversas do Altair?") != QMessageBox.Yes:
                return
            data = session.memory()
            data.update(context=content, enabled=True)
            session.save_memory(data)
            sync()
        except Exception:
            QMessageBox.warning(dialog, "Memória", "Não foi possível importar o arquivo.")

    def erase():
        if QMessageBox.question(dialog, "Memória", "Apagar o contexto e histórico locais desta conta?") == QMessageBox.Yes:
            try:
                session.save_memory({"enabled": False})
            except Exception:
                QMessageBox.warning(dialog, "Memória", "Não foi possível apagar a memória.")
            sync()


    def sync():
        account = session.load()
        status.setText(("Conta: " + (account.get("email") or "registrada") + "\n") if account.get("client_id") else "Sem conta registrada.\n")
        status.setText(status.text() + ("Uso do plano autorizado." if session.authorized() else "Uso do plano não autorizado."))
        logout.setEnabled(bool(account.get("access_token")))
        refresh.setEnabled(session.authorized() and consent.isChecked())
        login.setEnabled(consent.isChecked())
        apply.setEnabled(session.authorized() and consent.isChecked() and main.count() > 0)
        memory.blockSignals(True)
        memory.setChecked(session.memory().get("enabled") is True)
        memory.blockSignals(False)
        memory.setEnabled(session.authorized())
        import_context.setEnabled(session.authorized() and memory.isChecked())
        clear_memory.setEnabled(bool(account.get("client_id")))

    def models():
        try:
            items = _background(dialog, "Consultar modelos", session.models)
            main.clear()
            router.clear()
            for slug, name in items:
                main.addItem(name, slug)
                router.addItem(name, slug)
            for combo, key in [(main, "model_main"), (router, "model_router")]:
                index = combo.findData(initial.get(key))
                if index >= 0:
                    combo.setCurrentIndex(index)
            if not items:
                QMessageBox.warning(dialog, "ChatGPT", "Nenhum modelo disponível para esta conta.")
        except PlanError as exc:
            QMessageBox.warning(dialog, "ChatGPT", str(exc))
        sync()

    def connect():
        try:
            _background(dialog, "Conectar ChatGPT", session.sign_in)
            if session.authorized():
                models()
        except PlanError as exc:
            QMessageBox.warning(dialog, "ChatGPT", str(exc))
        sync()

    def disconnect():
        try:
            revoked = _background(dialog, "Desconectar ChatGPT", session.sign_out)
            if not revoked:
                QMessageBox.warning(dialog, "ChatGPT", "Sessão local removida. Confirme a revogação nas configurações do ChatGPT.")
        except PlanError as exc:
            QMessageBox.warning(dialog, "ChatGPT", str(exc))
        main.clear()
        router.clear()
        sync()

    def save():
        if not session.authorized() or not consent.isChecked() or not main.currentData():
            return
        result.update(provider="chatgpt_plan", api_key="", base_url="https://api.openai.com/v1/responses",
                      model_main=main.currentData(), model_router=router.currentData())
        dialog.accept()

    memory.toggled.connect(change_memory)
    import_context.clicked.connect(import_file)
    clear_memory.clicked.connect(erase)
    consent.toggled.connect(sync)
    login.clicked.connect(connect)
    logout.clicked.connect(disconnect)
    refresh.clicked.connect(models)
    apply.clicked.connect(save)
    sync()
    dialog.exec_()
    return result or None


class AvatarFace(QWidget):
    """Vector holographic avatar, animated with measured amplitude, no 3D dependencies."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(190)
        self.level = 0.0
        self.phase = 0.0
        self.active = False

    def frame(self, level, active=False):
        self.level += (min(1.0, max(0.0, level * 9)) - self.level) * 0.38
        self.phase += 0.07
        self.active = active
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        scale = min(self.width()/320, self.height()/220)
        p.translate(self.width()/2, self.height()/2)
        p.scale(scale, scale)
        p.translate(-160, -110)
        glow = QRadialGradient(160, 105, 105)
        glow.setColorAt(0, QColor(20, 126, 180, 85))
        glow.setColorAt(1, QColor(20, 126, 180, 0))
        p.setPen(Qt.NoPen)
        p.setBrush(QBrush(glow))
        p.drawEllipse(QRectF(55, 0, 210, 210))
        p.setBrush(Qt.NoBrush)
        for i, radius in enumerate((79, 93, 103)):
            pen = QPen(QColor(48, 166, 211, 110), 1)
            p.setPen(pen)
            p.drawArc(QRectF(160-radius, 105-radius, radius*2, radius*2),
                      int((self.phase*50 + i*80)*16), 275*16)
        poly = [(111,40),(209,40),(228,78),(218,143),(183,177),(137,177),(102,143),(92,78)]
        p.setBrush(QColor("#102d40"))
        p.setPen(QPen(QColor("#6acde9"), 1.7))
        p.drawPolygon(QPolygonF([QPointF(x,y) for x,y in poly]))
        p.setPen(QPen(QColor("#317b99"), 1.2))
        for x1,y1,x2,y2 in [(111,40,130,78),(209,40,190,78),(130,78,190,78),
                            (92,78,118,107),(228,78,202,107),(118,107,160,125),
                            (202,107,160,125),(137,177,160,150),(183,177,160,150)]:
            p.drawLine(QPointF(x1,y1),QPointF(x2,y2))
        blink = 2 if int(self.phase*10)%61 in (0,1) else 8
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#b3f2ff" if self.active else "#7ddbf7"))
        p.drawRoundedRect(QRectF(113,92-blink/2,32,blink),3,3)
        p.drawRoundedRect(QRectF(175,92-blink/2,32,blink),3,3)
        p.setPen(QPen(QColor("#7fdefa"), 2))
        p.setBrush(QColor("#091925"))
        h = 2 + 16*self.level
        p.drawRoundedRect(QRectF(143,139-h/2,34,h),3,3)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#5ccdef"))
        for i in range(39):
            h = 3 + (2 + 25*self.level)*abs(math.sin(i*1.4+self.phase*3))
            p.drawRoundedRect(QRectF(82+i*4,202-h/2,2.5,h),1,1)
        p.end()


class ChatGPTCompanion(QDialog):
    """Local companion, separate from the official ChatGPT session."""
    def __init__(self, parent=None, get_llm=None):
        super().__init__(parent, Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Altair — companheiro visual")
        self.resize(390, 560)
        self.setStyleSheet("QDialog {background:#101e2b;color:#d4f5ff;} QLabel {color:#d4f5ff;} QPushButton {padding:7px;} QCheckBox{color:#d4f5ff;}")
        self._stop = threading.Event()
        self._thread = None
        self._level = 0.0
        self._failure = False
        self._parent = parent
        self._get_llm = get_llm
        layout = QVBoxLayout(self)
        self.face = AvatarFace(self)
        layout.addWidget(self.face)
        self.state = QLabel("Altair • ChatGPT oficial em janela separada")
        self.state.setWordWrap(True)
        layout.addWidget(self.state)
        launch = QPushButton("Abrir ChatGPT oficial")
        launch.clicked.connect(lambda: webbrowser.open("https://chatgpt.com/"))
        layout.addWidget(launch)
        self.audio = QCheckBox("Animar com o áudio do computador")
        self.audio.toggled.connect(self._toggle)
        layout.addWidget(self.audio)
        info = QLabel("O medidor reage a todos os sons do PC, não apenas ao ChatGPT. Não grava, transcreve ou envia áudio.")
        info.setWordWrap(True)
        layout.addWidget(info)

        self.prompt = QLineEdit()
        self.prompt.setPlaceholderText("Comando para o Altair local…")
        layout.addWidget(self.prompt)
        actions = QHBoxLayout()
        send = QPushButton("Enviar ao Altair")
        send.clicked.connect(self._send)
        self.prompt.returnPressed.connect(self._send)
        actions.addWidget(send)
        stop = QPushButton("Parar fala")
        stop.clicked.connect(self._stop_speech)
        actions.addWidget(stop)
        layout.addLayout(actions)
        diagnostics = QPushButton("Diagnóstico do computador")
        diagnostics.clicked.connect(self._diagnostics)
        layout.addWidget(diagnostics)
        repo = QPushButton("Ver projeto Git local")
        repo.clicked.connect(self._git)
        layout.addWidget(repo)
        vision = QPushButton("Analisar imagem da tela (ChatGPT)")
        vision.clicked.connect(self._capture)
        layout.addWidget(vision)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._frame)
        self.timer.start(50)

    def _send(self):
        text = self.prompt.text().strip()
        if not text or self._parent is None:
            return
        if QMessageBox.question(self, "Altair local", "Enviar este comando ao Altair? Ele pode acionar as automações existentes.") != QMessageBox.Yes:
            return
        # Use the original UI's public chat pipeline; never send to the official website.
        self._parent.entry.setPlainText(text)
        self._parent._enviar()
        self.prompt.clear()

    def _stop_speech(self):
        if self._parent is not None:
            try:
                self._parent._stop_speech()
            except Exception:
                pass

    def _show_text(self, title, function):
        try:
            text = _background(self, title, function)
        except PlanError as exc:
            QMessageBox.warning(self, title, str(exc))
            return
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.resize(560, 400)
        layout = QVBoxLayout(dialog)
        view = QPlainTextEdit()
        view.setReadOnly(True)
        view.setPlainText(text)
        layout.addWidget(view)
        copy = QPushButton("Copiar resultado")
        copy.clicked.connect(view.selectAll)
        copy.clicked.connect(view.copy)
        layout.addWidget(copy)
        dialog.exec_()

    def _diagnostics(self):
        from altair.core.companion_tools import system_summary
        self._show_text("Diagnóstico local", system_summary)

    def _git(self):
        from altair.core.companion_tools import git_summary
        path = QFileDialog.getExistingDirectory(self, "Selecione um projeto Git local")
        if path:
            self._show_text("Git — somente leitura", lambda: git_summary(path))

    def _capture(self):
        llm = self._get_llm() if self._get_llm else None
        if llm is None or not hasattr(llm, "analyze_image"):
            QMessageBox.information(self, "Visão", "Selecione primeiro o provedor ChatGPT e um modelo compatível.")
            return
        if QMessageBox.question(self, "Visão", "Capturar a tela principal para uma prévia local? Revise a imagem antes de enviá-la.") != QMessageBox.Yes:
            return
        self.hide()
        QTimer.singleShot(350, lambda: self._preview_capture(llm))

    def _preview_capture(self, llm):
        screen = QApplication.primaryScreen()
        pix = screen.grabWindow(0) if screen else None
        self.show()
        if pix is None or pix.isNull():
            QMessageBox.warning(self, "Visão", "Não foi possível capturar a tela.")
            return
        # Restrict size and never write the screenshot to a file.
        if max(pix.width(), pix.height()) > 1920:
            pix = pix.scaled(1920, 1920, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        dlg = QDialog(self)
        dlg.setWindowTitle("Revise a captura antes de compartilhar")
        layout = QVBoxLayout(dlg)
        note = QLabel("A imagem pode conter dados privados. Só confirme se desejar enviá-la ao modelo ChatGPT selecionado.")
        note.setWordWrap(True)
        layout.addWidget(note)
        label = QLabel()
        label.setPixmap(pix.scaled(720, 430, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        question = QLineEdit("O que está acontecendo nesta tela?")
        layout.addWidget(question)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Enviar imagem ao ChatGPT")
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        layout.addWidget(buttons)
        if dlg.exec_() != QDialog.Accepted or not question.text().strip():
            return
        buffer = QBuffer()
        if not buffer.open(QIODevice.WriteOnly) or not pix.save(buffer, "PNG"):
            QMessageBox.warning(self, "Visão", "Falha ao preparar a imagem.")
            return
        png = bytes(buffer.data())
        buffer.close()
        prompt = question.text().strip()
        self._show_text("Análise da tela", lambda: llm.analyze_image(png, prompt))

    def _toggle(self, checked):
        if not checked:
            self._stop.set()
            self._level = 0
            return
        if self._thread and self._thread.is_alive():
            self.audio.setChecked(False)
            return
        self._stop = threading.Event()
        self._failure = False
        stop = self._stop

        def meter():
            try:
                import numpy as np
                import soundcard as sc
                speaker = sc.default_speaker()
                mic = sc.get_microphone(id=str(speaker.name), include_loopback=True)
                with mic.recorder(samplerate=48000, blocksize=2048) as recorder:
                    while not stop.is_set():
                        samples = recorder.record(numframes=2048)
                        self._level = float(np.sqrt(np.mean(samples ** 2)))
            except Exception:
                self._failure = True
            finally:
                self._level = 0.0

        self._thread = threading.Thread(target=meter, daemon=True)
        self._thread.start()

    def _frame(self):
        if self._failure:
            self.audio.setChecked(False)
            self.state.setText("Medidor indisponível neste dispositivo.")
            self._failure = False
        talking = self.audio.isChecked() and self._level > 0.012
        busy = bool(getattr(self._parent, "_processing_count", 0))
        self.face.frame(self._level if talking else 0, busy or talking)
        if busy:
            self.state.setText("Altair local processando…")
        elif talking:
            self.state.setText("Áudio do PC ativo")
        elif self.audio.isChecked():
            self.state.setText("Aguardando áudio do PC")
        else:
            self.state.setText("Altair • ChatGPT oficial em janela separada")

    def done(self, result):
        self._stop.set()
        self.timer.stop()
        super().done(result)

    def closeEvent(self, event):
        self._stop.set()
        self.timer.stop()
        super().closeEvent(event)
