import sys
import os
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
from typing import Optional, Dict, List, Set

from peer import Peer

class PeerGUI:
    def __init__(self, peer_id: int, files_path: Optional[str] = None):
        """
        Interface gráfica para o peer

        Args:
            peer_id: ID do peer
            files_path: Caminho para os arquivos do peer
        """
        self.peer = Peer(peer_id, files_path)

        # Configurar janela principal
        self.root = tk.Tk()
        self.root.title(f"Peer {peer_id}")
        self.root.geometry("800x600")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        # Iniciar peer em uma thread separada
        threading.Thread(target=self.peer.start, daemon=True).start()

        # Configurar interface
        self._setup_ui()

        # Temporizador para atualizar informações
        self._schedule_updates()

    def _setup_ui(self):
        """Configura a interface gráfica"""
        # Barra de status
        self.status_frame = ttk.Frame(self.root)
        self.status_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        self.status_label = ttk.Label(self.status_frame, text="Iniciando...")
        self.status_label.pack(side=tk.LEFT, padx=5)

        self.tracker_label = ttk.Label(self.status_frame, text="Tracker: Desconhecido")
        self.tracker_label.pack(side=tk.RIGHT, padx=5)

        # Frame principal com tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)

        # Tab de arquivos locais
        self.local_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.local_frame, text="Arquivos Locais")

        # Tab de arquivos da rede
        self.network_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.network_frame, text="Arquivos da Rede")

        # Tab de busca e download
        self.search_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.search_frame, text="Buscar e Baixar")

        # Tab de informações do tracker
        self.tracker_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.tracker_frame, text="Informações do Tracker")

        # Configurar cada tab
        self._setup_local_tab()
        self._setup_network_tab()
        self._setup_search_tab()
        self._setup_tracker_tab()

    def _setup_local_tab(self):
        """Configura a aba de arquivos locais"""
        # Frame de controle
        control_frame = ttk.Frame(self.local_frame)
        control_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        ttk.Button(control_frame, text="Adicionar Arquivo", command=self._add_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Remover Arquivo", command=self._remove_file).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Atualizar", command=self._update_local_files).pack(side=tk.RIGHT, padx=5)

        # Lista de arquivos
        files_frame = ttk.Frame(self.local_frame)
        files_frame.pack(side=tk.TOP, expand=True, fill=tk.BOTH, padx=5, pady=5)

        self.local_files_listbox = tk.Listbox(files_frame)
        scrollbar = ttk.Scrollbar(files_frame, orient="vertical", command=self.local_files_listbox.yview)
        self.local_files_listbox.configure(yscrollcommand=scrollbar.set)

        self.local_files_listbox.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _setup_network_tab(self):
        """Configura a aba de arquivos da rede"""
        # Frame de controle
        control_frame = ttk.Frame(self.network_frame)
        control_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        # Botão para baixar arquivo selecionado
        ttk.Button(control_frame, text="Baixar Arquivo", command=self._download_network_file).pack(side=tk.LEFT, padx=5)

        ttk.Button(control_frame, text="Atualizar", command=self._update_network_files).pack(side=tk.RIGHT, padx=5)

        # Treeview para mostrar os arquivos da rede
        tree_frame = ttk.Frame(self.network_frame)
        tree_frame.pack(side=tk.TOP, expand=True, fill=tk.BOTH, padx=5, pady=5)

        columns = ("peer_id", "filename")
        self.network_tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        self.network_tree.heading("peer_id", text="Peer ID")
        self.network_tree.heading("filename", text="Arquivo")

        self.network_tree.column("peer_id", width=100)
        self.network_tree.column("filename", width=300)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.network_tree.yview)
        self.network_tree.configure(yscrollcommand=scrollbar.set)

        self.network_tree.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def _setup_search_tab(self):
        """Configura a aba de busca e download"""
        # Frame de busca
        search_control = ttk.Frame(self.search_frame)
        search_control.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        ttk.Label(search_control, text="Arquivo:").pack(side=tk.LEFT, padx=5)
        self.search_entry = ttk.Entry(search_control, width=30)
        self.search_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(search_control, text="Buscar", command=self._search_file).pack(side=tk.LEFT, padx=5)

        # Lista de resultados
        results_frame = ttk.Frame(self.search_frame)
        results_frame.pack(side=tk.TOP, expand=True, fill=tk.BOTH, padx=5, pady=5)

        columns = ("peer_id", "filename")
        self.search_results_tree = ttk.Treeview(results_frame, columns=columns, show="headings")
        self.search_results_tree.heading("peer_id", text="Peer ID")
        self.search_results_tree.heading("filename", text="Arquivo")

        self.search_results_tree.column("peer_id", width=100)
        self.search_results_tree.column("filename", width=300)

        scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.search_results_tree.yview)
        self.search_results_tree.configure(yscrollcommand=scrollbar.set)

        self.search_results_tree.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Frame de download
        download_frame = ttk.Frame(self.search_frame)
        download_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)

        ttk.Button(download_frame, text="Baixar Arquivo Selecionado", command=self._download_selected_file).pack(side=tk.LEFT, padx=5)

    def _setup_tracker_tab(self):
        """Configura a aba de informações do tracker"""
        # Informações do tracker
        info_frame = ttk.Frame(self.tracker_frame)
        info_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)

        self.tracker_info_label = ttk.Label(info_frame, text="Informações do Tracker")
        self.tracker_info_label.pack(side=tk.TOP, padx=5, pady=5)

        # Frame para estatísticas
        stats_frame = ttk.Frame(self.tracker_frame)
        stats_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Labels para estatísticas
        ttk.Label(stats_frame, text="Época atual:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.current_epoch_label = ttk.Label(stats_frame, text="Desconhecido")
        self.current_epoch_label.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)

        ttk.Label(stats_frame, text="Status:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.tracker_status_label = ttk.Label(stats_frame, text="Desconhecido")
        self.tracker_status_label.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)

        ttk.Label(stats_frame, text="Último heartbeat:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.last_heartbeat_label = ttk.Label(stats_frame, text="Desconhecido")
        self.last_heartbeat_label.grid(row=2, column=1, sticky=tk.W, padx=5, pady=5)

        ttk.Label(stats_frame, text="Total de arquivos indexados:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.total_files_label = ttk.Label(stats_frame, text="Desconhecido")
        self.total_files_label.grid(row=3, column=1, sticky=tk.W, padx=5, pady=5)

        # Botão para forçar eleição (simular falha do tracker)
        force_election_frame = ttk.Frame(self.tracker_frame)
        force_election_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)

        ttk.Button(force_election_frame, text="Forçar Eleição", command=self._force_election).pack(side=tk.LEFT, padx=5)
        ttk.Button(force_election_frame, text="Atualizar Informações", command=self._update_tracker_info).pack(side=tk.RIGHT, padx=5)

    def _schedule_updates(self):
        """Agenda atualizações periódicas da interface"""
        # Atualizar informações a cada 1 segundo
        self._update_status()
        self.root.after(1000, self._schedule_updates)

    def _update_status(self):
        """Atualiza a barra de status"""
        # Atualizar status do tracker
        if self.peer.is_tracker:
            self.status_label.config(text=f"Status: Este peer é o Tracker atual (Época {self.peer.current_epoch})")
        else:
            # Verificar se há um tracker disponível
            if self.peer.tracker_proxy:
                try:
                    self.peer.tracker_proxy.ping()  # Verificar se o tracker responde
                    self.status_label.config(text=f"Status: Conectado (Época {self.peer.current_epoch})")
                except Exception:
                    self.status_label.config(text="Status: Tracker não responde")
            else:
                self.status_label.config(text="Status: Tracker não encontrado")

        # Atualizar label do tracker
        if self.peer.is_tracker:
            self.tracker_label.config(text="Tracker: Este peer")
        elif self.peer.tracker_uri:
            self.tracker_label.config(text=f"Tracker: {str(self.peer.tracker_uri).split('@')[1].split(':')[0]}")
        else:
            self.tracker_label.config(text="Tracker: Desconhecido")

    def _update_local_files(self):
        """Atualiza a lista de arquivos locais"""
        self.local_files_listbox.delete(0, tk.END)

        files = self.peer.get_local_files()
        for file in sorted(files):
            self.local_files_listbox.insert(tk.END, file)

    def _update_network_files(self):
        """Atualiza a lista de arquivos da rede"""
        self.network_tree.delete(*self.network_tree.get_children())

        file_index = self.peer.get_all_network_files()

        for peer_id, files in file_index.items():
            for file in files:
                self.network_tree.insert("", tk.END, values=(peer_id, file))

    def _update_tracker_info(self):
        """Atualiza as informações do tracker"""
        self.current_epoch_label.config(text=str(self.peer.current_epoch))

        # Status do tracker
        if self.peer.is_tracker:
            self.tracker_status_label.config(text="Este peer é o tracker")
        elif hasattr(self.peer, 'succedded_heartbeat') and self.peer.succedded_heartbeat:
            self.tracker_status_label.config(text="Conectado")
        else:
            self.tracker_status_label.config(text="Não encontrado")

        # Último heartbeat
        if self.peer.last_heartbeat > 0:
            last_heartbeat_time = time.strftime("%H:%M:%S", time.localtime(self.peer.last_heartbeat))
            seconds_ago = time.time() - self.peer.last_heartbeat
            self.last_heartbeat_label.config(text=f"{last_heartbeat_time} ({seconds_ago:.1f}s atrás)")
        else:
            self.last_heartbeat_label.config(text="Nunca recebido")

        # Total de arquivos indexados
        total_files = 0
        file_index = self.peer.get_all_network_files()
        for peer_id, files in file_index.items():
            total_files += len(files)

        self.total_files_label.config(text=str(total_files))

    def _search_file(self):
        """Busca um arquivo na rede"""
        filename = self.search_entry.get().strip()
        if not filename:
            messagebox.showwarning("Busca de Arquivo", "Digite o nome do arquivo a ser buscado.")
            return

        # Limpar resultados anteriores
        self.search_results_tree.delete(*self.search_results_tree.get_children())

        # Buscar arquivo no tracker
        peers_with_file = self.peer.search_file_from_tracker(filename)

        if not peers_with_file:
            messagebox.showinfo("Busca de Arquivo", f"Arquivo '{filename}' não encontrado na rede.")
            return

        # Mostrar resultados
        for peer_id in peers_with_file:
            self.search_results_tree.insert("", tk.END, values=(peer_id, filename))

    def _download_selected_file(self):
        """Baixa o arquivo selecionado na aba de busca"""
        selected_item = self.search_results_tree.selection()
        if not selected_item:
            messagebox.showwarning("Download de Arquivo", "Selecione um arquivo para baixar.")
            return

        # Obter informações do arquivo selecionado
        item_values = self.search_results_tree.item(selected_item[0], "values")
        peer_id = int(item_values[0])
        filename = item_values[1]

        # Verificar se o arquivo já existe localmente
        if filename in self.peer.get_local_files():
            response = messagebox.askyesno(
                "Download de Arquivo",
                f"O arquivo '{filename}' já existe localmente. Deseja substituí-lo?"
            )
            if not response:
                return

        # Iniciar download em uma thread separada
        def download_thread():
            success = self.peer.download_file_from_peer(peer_id, filename)

            # Atualizar interface após o download
            if success:
                messagebox.showinfo("Download de Arquivo", f"Arquivo '{filename}' baixado com sucesso.")
                self._update_local_files()
            else:
                messagebox.showerror("Download de Arquivo", f"Erro ao baixar arquivo '{filename}'.")

        threading.Thread(target=download_thread).start()

    def _download_network_file(self):
        """Baixa o arquivo selecionado na aba de arquivos da rede"""
        selected_item = self.network_tree.selection()
        if not selected_item:
            messagebox.showwarning("Download de Arquivo", "Selecione um arquivo para baixar.")
            return

        # Obter informações do arquivo selecionado
        item_values = self.network_tree.item(selected_item[0], "values")
        peer_id = int(item_values[0])
        filename = item_values[1]

        # Verificar se o arquivo pertence ao próprio peer
        if peer_id == self.peer.peer_id:
            messagebox.showinfo("Download de Arquivo", "Este arquivo já está em seu peer.")
            return

        # Verificar se o arquivo já existe localmente
        if filename in self.peer.get_local_files():
            response = messagebox.askyesno(
                "Download de Arquivo",
                f"O arquivo '{filename}' já existe localmente. Deseja substituí-lo?"
            )
            if not response:
                return

        # Iniciar download em uma thread separada
        def download_thread():
            success = self.peer.download_file_from_peer(peer_id, filename)

            # Atualizar interface após o download
            if success:
                messagebox.showinfo("Download de Arquivo", f"Arquivo '{filename}' baixado com sucesso.")
                self._update_local_files()
            else:
                messagebox.showerror("Download de Arquivo", f"Erro ao baixar arquivo '{filename}'.")

        threading.Thread(target=download_thread).start()

    def _add_file(self):
        """Adiciona um novo arquivo ao peer"""
        # Abrir diálogo para selecionar arquivo
        file_path = filedialog.askopenfilename(title="Selecionar Arquivo")
        if not file_path:
            return

        filename = os.path.basename(file_path)

        # Verificar se o arquivo já existe
        if filename in self.peer.get_local_files():
            response = messagebox.askyesno(
                "Adicionar Arquivo",
                f"O arquivo '{filename}' já existe. Deseja substituí-lo?"
            )
            if not response:
                return

        # Ler conteúdo do arquivo
        try:
            with open(file_path, "rb") as f:
                content = f.read()

            # Adicionar arquivo ao peer
            success = self.peer.add_file(filename, content)

            if success:
                messagebox.showinfo("Adicionar Arquivo", f"Arquivo '{filename}' adicionado com sucesso.")
                self._update_local_files()
            else:
                messagebox.showerror("Adicionar Arquivo", f"Erro ao adicionar arquivo '{filename}'.")
        except Exception as e:
            messagebox.showerror("Adicionar Arquivo", f"Erro ao ler arquivo: {e}")

    def _remove_file(self):
        """Remove um arquivo do peer"""
        selected_item = self.local_files_listbox.curselection()
        if not selected_item:
            messagebox.showwarning("Remover Arquivo", "Selecione um arquivo para remover.")
            return

        filename = self.local_files_listbox.get(selected_item[0])

        response = messagebox.askyesno(
            "Remover Arquivo",
            f"Deseja realmente remover o arquivo '{filename}'?"
        )
        if not response:
            return

        # Remover arquivo
        success = self.peer.remove_file(filename)

        if success:
            messagebox.showinfo("Remover Arquivo", f"Arquivo '{filename}' removido com sucesso.")
            self._update_local_files()
        else:
            messagebox.showerror("Remover Arquivo", f"Erro ao remover arquivo '{filename}'.")

    def _force_election(self):
        """Força uma eleição (simula falha do tracker)"""
        response = messagebox.askyesno(
            "Forçar Eleição",
            "Isso simulará uma falha do tracker atual e iniciará uma nova eleição. Continuar?"
        )
        if not response:
            return

        # Iniciar eleição
        self.peer.start_election()
        messagebox.showinfo("Forçar Eleição", "Eleição iniciada.")

    def on_close(self):
        """Manipulador para evento de fechamento da janela"""
        # Se este peer for o tracker, avisar o usuário
        if self.peer.is_tracker:
            response = messagebox.askyesno(
                "Sair",
                "Este peer é o tracker atual. Sair agora causará uma nova eleição. Continuar?"
            )
            if not response:
                return

        # Encerrar aplicação
        self.root.destroy()

    def run(self):
        """Inicia a interface gráfica"""
        # Atualizar listas iniciais
        self._update_local_files()
        self._update_network_files()
        self._update_tracker_info()

        # Iniciar loop principal
        self.root.mainloop()
