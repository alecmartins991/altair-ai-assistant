"""Desktop controls for the ChatGPT plan and a separate visual companion."""
import threading
import webbrowser

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, QComboBox,
                             QMessageBox, QCheckBox, QFileDialog)
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


class ChatGPTCompanion(QDialog):
    """Optional avatar for the official ChatGPT site; not a session bridge.

    The meter computes amplitude only, from all system output, when enabled.
    No recorded samples are saved, transcribed or transmitted.
    """
    def __init__(self, parent=None):
        super().__init__(parent, Qt.Tool | Qt.WindowStaysOnTopHint)
        self.setWindowTitle("Altair — companheiro visual")
        self.resize(330, 300)
        self.setStyleSheet("QDialog {background:#101e2b;color:#d4f5ff;} QLabel {color:#d4f5ff;} QPushButton {padding:8px;}")
        self._stop = threading.Event()
        self._thread = None
        self._level = 0.0
        self._failure = False
        layout = QVBoxLayout(self)
        self.face = QLabel("◉     ◉\n   ─   ")
        self.face.setAlignment(Qt.AlignCenter)
        self.face.setStyleSheet("font-size:48px;color:#72dfff;background:#152e43;border-radius:24px;padding:16px;")
        layout.addWidget(self.face)
        self.state = QLabel("Modo visual • sem conexão à conversa")
        self.state.setWordWrap(True)
        layout.addWidget(self.state)
        launch = QPushButton("Abrir ChatGPT oficial")
        launch.clicked.connect(lambda: webbrowser.open("https://chatgpt.com/"))
        layout.addWidget(launch)
        self.audio = QCheckBox("Animar com áudio do computador (opcional)")
        self.audio.setStyleSheet("color:#d4f5ff;")
        layout.addWidget(self.audio)
        self.audio.toggled.connect(self._toggle)
        info = QLabel("Reage ao volume de todos os sons do PC. Não identifica a voz do ChatGPT nem sincroniza mensagens.")
        info.setWordWrap(True)
        layout.addWidget(info)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._frame)
        self.timer.start(70)

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
            self.state.setText("Medidor de áudio indisponível neste dispositivo.")
            self._failure = False
            return
        if not self.audio.isChecked():
            self.face.setText("◉     ◉\n   ─   ")
            return
        talking = self._level > 0.012
        self.face.setText("◉     ◉\n   " + ("◯" if talking else "─") + "   ")
        self.state.setText("Áudio do PC ativo" if talking else "Aguardando áudio do PC")

    def done(self, result):
        self._stop.set()
        self.timer.stop()
        super().done(result)
