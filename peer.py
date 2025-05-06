import os
import time
import random
import threading
import Pyro5.api
import base64
from Pyro5.errors import PyroError
from typing import List, Dict, Set, Optional, Tuple

# Configurações do Pyro5 para melhorar a conexão
Pyro5.config.SERIALIZER = "serpent"
Pyro5.config.THREADPOOL_SIZE = 16
Pyro5.config.SERVERTYPE = "multiplex"
Pyro5.config.DETAILED_TRACEBACK = True
Pyro5.config.SOCK_REUSE = True
Pyro5.config.COMMTIMEOUT = 5.0

# Configuração básica de logging
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Caminho onde os arquivos do peer serão armazenados
DEFAULT_FILES_PATH = "files"

class Peer:
    def __init__(self, peer_id: int, files_path: str = None):
        """
        Inicializa um nó peer

        Args:
            peer_id: Identificador único do peer
            files_path: Diretório onde os arquivos do peer estão armazenados
        """
        self.peer_id = peer_id
        self.logger = logging.getLogger(f"Peer-{peer_id}")
        self.files_path = files_path or os.path.join(DEFAULT_FILES_PATH, f"peer_{peer_id}")


        os.makedirs(self.files_path, exist_ok=True)


        self.files: Set[str] = set()
        self._scan_local_files()


        self.tracker_uri = None
        self.tracker_proxy = None
        self.current_epoch = 0


        self.is_tracker = False
        self.voted_for_epoch = 0
        self.votes_received = set()
        self.election_in_progress = False


        self.tracker_timeout = random.randint(150, 300) / 1000
        self.last_heartbeat = 0
        self.succedded_heartbeat = False
        self.heartbeat_timer = None

        self.logger.info(f"Peer {peer_id} iniciado. Arquivos em: {self.files_path}")
        self.logger.info(f"Arquivos locais: {self.files}")

    @Pyro5.api.expose
    def heartbeat(self, epoch: int) -> bool:
        """
        Recebe heartbeat do tracker

        Args:
            epoch: Época atual do tracker

        Returns:
            True se o heartbeat for válido
        """
        self.is_tracker = False
        if epoch > self.current_epoch:

            self.logger.info(f"Detected new tracker with epoch {epoch}, re-registering files")
            self.current_epoch = epoch
            self.last_heartbeat = time.time()

            self._register_files_with_tracker()

            self._reset_tracker_timer()
            self.succedded_heartbeat = True
            return True
        elif epoch == self.current_epoch:
            self.last_heartbeat = time.time()

            self._reset_tracker_timer()
            self.succedded_heartbeat = True
            return True
        self.succedded_heartbeat = False
        return False

    def _reset_tracker_timer(self):
        """Reinicia o temporizador de detecção de falha do tracker"""

        if self.heartbeat_timer:
            self.heartbeat_timer.cancel()


        self.tracker_timeout = random.randint(150, 300) / 1000
        self.heartbeat_timer = threading.Timer(self.tracker_timeout, self._check_tracker_status)
        self.heartbeat_timer.daemon = True
        self.heartbeat_timer.start()

    def _check_tracker_status(self):
        """Verifica se o tracker está ativo, inicia eleição se necessário"""
        current_time = time.time()
        if current_time - self.last_heartbeat > self.tracker_timeout:
            self.logger.info(f"Timeout do tracker detectado. Último heartbeat há {current_time - self.last_heartbeat:.2f}s")

            try:
                if self.tracker_proxy:
                    self.tracker_proxy.ping()
                    self._reset_tracker_timer()
                    return
            except Exception:
                self.logger.info("Tracker não responde. Iniciando eleição.")
                self.start_election()
        else:
            self._reset_tracker_timer()

    def start_election(self):
        """Inicia uma eleição para um novo tracker"""
        if self.election_in_progress:
            self.logger.info("Eleição já em andamento, ignorando nova solicitação")
            return


        new_epoch = self.current_epoch + 1
        self.logger.info(f"Iniciando eleição para época {new_epoch}")

        self.election_in_progress = True
        self.votes_received = {self.peer_id}
        self.voted_for_epoch = new_epoch

        delay = random.uniform(0.5, 2.0)
        time.sleep(delay)

        try:
            name_server = Pyro5.api.locate_ns()
            peers = {name: uri for name, uri in name_server.list(prefix="peer.").items()}

            self.logger.info(f"Encontrados {len(peers)} peers no serviço de nomes")

            for peer_name, uri in peers.items():
                peer_id = int(peer_name.split(".")[1])
                if peer_id != self.peer_id:
                    try:
                        peer_proxy = Pyro5.api.Proxy(uri)
                        peer_proxy._pyroTimeout = 5.0
                        self.logger.info(f"Solicitando voto do peer {peer_id}")
                        vote_granted = peer_proxy.request_vote(self.peer_id, new_epoch)
                        if vote_granted:
                            self.votes_received.add(peer_id)
                            self.logger.info(f"Recebeu voto do peer {peer_id}")
                        else:
                            self.logger.info(f"Peer {peer_id} negou o voto")
                    except Exception as e:
                        self.logger.warning(f"Erro ao solicitar voto de {peer_name}: {e}")


            total_peers = len(peers) + 1
            votes_needed = total_peers // 2 + 1
            self.logger.info(f"Resultado da eleição: {len(self.votes_received)} votos de {total_peers} peers (necessário: {votes_needed})")

            if len(self.votes_received) >= votes_needed:
                self.logger.info(f"Eleição vencida com {len(self.votes_received)} votos de {total_peers} peers")
                self._become_tracker(new_epoch)
            else:
                self.logger.info(f"Eleição perdida. Recebeu {len(self.votes_received)} votos, mas precisa de >{total_peers//2}")
                self.election_in_progress = False


                retry_delay = random.uniform(0.5, 2.0)
                self.logger.info(f"Aguardando {retry_delay:.2f}s antes de considerar nova eleição")
                time.sleep(retry_delay)

        except Exception as e:
            self.logger.error(f"Erro durante eleição: {e}")
            self.election_in_progress = False

            self._reset_tracker_timer()

    def _become_tracker(self, epoch: int):
        """Torna-se o novo tracker"""
        self.current_epoch = epoch
        self.is_tracker = True
        self.election_in_progress = False


        try:
            tracker_name = f"Tracker_Epoca_{epoch}"
            self.logger.info(f"Registrando-se como {tracker_name}")
            name_server = Pyro5.api.locate_ns()


            old_trackers = [name for name in name_server.list().keys() if name.startswith("Tracker_Epoca_")]
            for old_name in old_trackers:
                try:
                    name_server.remove(old_name)
                except Exception as e:
                    self.logger.warning(f"Erro ao remover tracker antigo {old_name}: {e}")


            if not hasattr(self, 'file_index'):
                self.file_index = {}
            self.file_index[self.peer_id] = self.files


            uri = self._pyroDaemon.uriFor(self)
            name_server.register(tracker_name, uri)
            self.logger.info(f"Registrado como {tracker_name} com URI {uri}")


            self._start_heartbeat_thread(epoch)
        except Exception as e:
            self.logger.error(f"Erro ao registrar-se como tracker: {e}")
            self.is_tracker = False

    @Pyro5.api.expose
    def request_vote(self, candidate_id: int, new_epoch: int) -> bool:
        """
        Recebe solicitação de voto de um candidato

        Args:
            candidate_id: ID do peer candidato
            new_epoch: Época da eleição

        Returns:
            True se o voto for concedido, False caso contrário
        """
        self.logger.info(f"Recebeu solicitação de voto do peer {candidate_id} para época {new_epoch}")



        if new_epoch > self.current_epoch:
            self.logger.info(f"Concedendo voto para peer {candidate_id} na época {new_epoch}")
            self.voted_for_epoch = new_epoch
            return True
        else:
            self.logger.info(f"Negando voto para peer {candidate_id}. Época atual: {self.current_epoch}, Última época votada: {self.voted_for_epoch}")
            return False

    def _start_heartbeat_thread(self, epoch: int):
        """Inicia thread para enviar heartbeats"""
        def send_heartbeats():
            while self.is_tracker:
                try:
                    name_server = Pyro5.api.locate_ns()
                    peers = {name: uri for name, uri in name_server.list(prefix="peer.").items()}


                    for peer_name, uri in peers.items():
                        peer_id = int(peer_name.split(".")[1])
                        if peer_id != self.peer_id:
                            try:
                                peer_proxy = Pyro5.api.Proxy(uri)
                                peer_proxy.heartbeat(epoch)
                            except Exception:
                                pass
                except Exception:
                    pass

                time.sleep(0.1)

        heartbeat_thread = threading.Thread(target=send_heartbeats, daemon=True)
        heartbeat_thread.start()

    def _scan_local_files(self):
        """Escaneia arquivos locais para atualizar a lista"""
        try:
            files = os.listdir(self.files_path)
            self.files = set(files)
        except Exception as e:
            self.logger.error(f"Erro ao escanear arquivos locais: {e}")

    def register_with_name_server(self):
        """Registra-se no serviço de nomes do PyRO"""
        try:
            name_server = Pyro5.api.locate_ns()
            peer_name = f"peer.{self.peer_id}"
            uri = self._pyroDaemon.uriFor(self)
            name_server.register(peer_name, uri)
            self.logger.info(f"Registrado no serviço de nomes como {peer_name}")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao registrar no serviço de nomes: {e}")
            return False

    def find_and_register_with_tracker(self):
      """Encontra e se registra com o tracker atual"""
      try:
          name_server = Pyro5.api.locate_ns()


          trackers = [name for name in name_server.list().keys() if name.startswith("Tracker_Epoca_")]

          if not trackers:
              self.logger.info("Nenhum tracker encontrado. Iniciando eleição.")
              self.start_election()
              return False


          max_epoch = max([int(t.split("_")[-1]) for t in trackers])
          tracker_name = f"Tracker_Epoca_{max_epoch}"
          self.tracker_uri = name_server.lookup(tracker_name)
          self.tracker_proxy = Pyro5.api.Proxy(self.tracker_uri)
          self.current_epoch = max_epoch

          self.logger.info(f"Encontrou tracker na época {max_epoch}")


          self._register_files_with_tracker()


          self.last_heartbeat = time.time()
          self._reset_tracker_timer()

          return True
      except Exception as e:
          self.logger.error(f"Erro ao buscar/registrar com tracker: {e}")

          self.logger.info("Falha ao encontrar tracker. Iniciando eleição.")
          self.start_election()
          return False

    def _register_files_with_tracker(self):
      """Registra arquivos locais com o tracker"""
      if not self.tracker_proxy:
          return False

      try:

          self._scan_local_files()


          name_server = Pyro5.api.locate_ns()
          trackers = [name for name in name_server.list().keys() if name.startswith("Tracker_Epoca_")]

          if not trackers:
              self.logger.error("Nenhum tracker registrado")
              return False


          max_epoch = max([int(t.split("_")[-1]) for t in trackers])
          tracker_name = f"Tracker_Epoca_{max_epoch}"
          tracker_uri = name_server.lookup(tracker_name)


          tracker_proxy = Pyro5.api.Proxy(tracker_uri)


          result = tracker_proxy.register_files(self.peer_id, list(self.files))
          self.logger.info(f"Arquivos registrados com o tracker: {result}")
          return result
      except Exception as e:
          self.logger.error(f"Erro ao registrar arquivos com tracker: {e}")
          return False

    @Pyro5.api.expose
    def register_files(self, peer_id: int, files: List[str]) -> bool:
        """
        [Função do Tracker] Registra arquivos de um peer

        Args:
            peer_id: ID do peer
            files: Lista de arquivos do peer

        Returns:
            True se o registro for bem-sucedido
        """
        if not self.is_tracker:
            return False

        self.logger.info(f"Registrando {len(files)} arquivos para peer {peer_id}")


        self.file_index[peer_id] = set(files)
        return True

    @Pyro5.api.expose
    def search_file(self, filename: str) -> List[int]:
        """
        [Função do Tracker] Busca peers que possuem um arquivo

        Args:
            filename: Nome do arquivo a ser buscado

        Returns:
            Lista de IDs de peers que possuem o arquivo
        """
        if not self.is_tracker:
            return []

        self.logger.info(f"Buscando arquivo {filename}")


        if not hasattr(self, 'file_index'):
            self.file_index = {}


        peers_with_file = []
        for peer_id, files in self.file_index.items():
            if filename in files:
                peers_with_file.append(peer_id)

        self.logger.info(f"Peers com arquivo {filename}: {peers_with_file}")
        return peers_with_file

    def search_file_from_tracker(self, filename: str) -> List[int]:
      """
      Busca no tracker por peers que possuem um arquivo

      Args:
          filename: Nome do arquivo a ser buscado

      Returns:
          Lista de IDs de peers que possuem o arquivo
      """
      try:

          name_server = Pyro5.api.locate_ns()
          trackers = [name for name in name_server.list().keys() if name.startswith("Tracker_Epoca_")]

          if not trackers:
              self.logger.error("Nenhum tracker registrado")
              return []


          max_epoch = max([int(t.split("_")[-1]) for t in trackers])
          tracker_name = f"Tracker_Epoca_{max_epoch}"
          tracker_uri = name_server.lookup(tracker_name)


          tracker_proxy = Pyro5.api.Proxy(tracker_uri)

          peers = tracker_proxy.search_file(filename)
          self.logger.info(f"Peers com arquivo {filename}: {peers}")
          return peers
      except Exception as e:
          self.logger.error(f"Erro ao buscar arquivo no tracker: {e}")
          return []
    @Pyro5.api.expose
    def download_file(self, filename: str) -> bytes:
        """
        Permite que outro peer faça download de um arquivo

        Args:
            filename: Nome do arquivo a ser baixado

        Returns:
            Conteúdo do arquivo em bytes
        """
        file_path = os.path.join(self.files_path, filename)

        try:
            with open(file_path, "rb") as f:
                content = f.read()

            self.logger.info(f"Enviando arquivo {filename} ({len(content)} bytes)")
            return content
        except Exception as e:
            self.logger.error(f"Erro ao enviar arquivo {filename}: {e}")
            return b""

    def download_file_from_peer(self, peer_id: int, filename: str) -> bool:
        """
        Faz download de um arquivo de outro peer

        Args:
            peer_id: ID do peer que possui o arquivo
            filename: Nome do arquivo a ser baixado

        Returns:
            True se o download for bem-sucedido
        """
        try:

            name_server = Pyro5.api.locate_ns()
            peer_uri = name_server.lookup(f"peer.{peer_id}")
            peer_proxy = Pyro5.api.Proxy(peer_uri)


            self.logger.info(f"Fazendo download de {filename} do peer {peer_id}")
            content = peer_proxy.download_file(filename)

            if not content:
                self.logger.error(f"Arquivo {filename} vazio ou não encontrado no peer {peer_id}")
                return False


            content = base64.b64decode(content['data'])


            file_path = os.path.join(self.files_path, filename)
            with open(file_path, "wb") as f:
                f.write(content)

            self.logger.info(f"Arquivo {filename} baixado com sucesso ({len(content)} bytes)")


            self.files.add(filename)


            success = False
            for _ in range(3):
                if self._register_files_with_tracker():
                    success = True
                    break
                time.sleep(0.5)

            if not success:
                self.logger.warning(f"Não foi possível registrar {filename} com o tracker após várias tentativas")

            return True
        except Exception as e:
            self.logger.error(f"Erro ao baixar arquivo {filename} do peer {peer_id}: {e}")
            return False

    @Pyro5.api.expose
    def ping(self) -> bool:
        """Simples ping para verificar se o peer está ativo"""
        return True

    def start(self):
      """Inicia o peer e registra no serviço de nomes"""

      try:

          daemon = Pyro5.api.Daemon(host='localhost')
          self._pyroDaemon = daemon


          uri = daemon.register(self)

          self.logger.info(f"Daemon iniciado com URI: {uri}")


          name_server = Pyro5.api.locate_ns()
          peer_name = f"peer.{self.peer_id}"
          name_server.register(peer_name, uri)
          self.logger.info(f"Registrado no serviço de nomes como {peer_name}")


          daemon_thread = threading.Thread(target=daemon.requestLoop, daemon=True)
          daemon_thread.start()


          time.sleep(1)


          self.find_and_register_with_tracker()

          return True
      except Exception as e:
          self.logger.error(f"Erro ao iniciar peer: {e}")
          return False

    def add_file(self, filename: str, content: bytes) -> bool:
        """
        Adiciona um novo arquivo ao peer

        Args:
            filename: Nome do arquivo
            content: Conteúdo do arquivo em bytes

        Returns:
            True se o arquivo for adicionado com sucesso
        """
        try:
            file_path = os.path.join(self.files_path, filename)
            with open(file_path, "wb") as f:
                f.write(content)

            self.logger.info(f"Arquivo {filename} adicionado localmente")


            self.files.add(filename)


            if not self.is_tracker:
                self._register_files_with_tracker()
            else:

                if not hasattr(self, 'file_index'):
                    self.file_index = {}
                self.file_index[self.peer_id] = self.files

            return True
        except Exception as e:
            self.logger.error(f"Erro ao adicionar arquivo {filename}: {e}")
            return False

    def remove_file(self, filename: str) -> bool:
        """
        Remove um arquivo do peer

        Args:
            filename: Nome do arquivo

        Returns:
            True se o arquivo for removido com sucesso
        """
        try:
            file_path = os.path.join(self.files_path, filename)
            if os.path.exists(file_path):
                os.remove(file_path)

                self.logger.info(f"Arquivo {filename} removido localmente")


                self.files.discard(filename)


                if not self.is_tracker:
                    self._register_files_with_tracker()
                else:

                    if not hasattr(self, 'file_index'):
                        self.file_index = {}
                    self.file_index[self.peer_id] = self.files

                return True
            return False
        except Exception as e:
            self.logger.error(f"Erro ao remover arquivo {filename}: {e}")
            return False

    def get_local_files(self) -> Set[str]:
        """Retorna a lista de arquivos locais"""
        self._scan_local_files()
        return self.files

    def get_all_network_files(self) -> Dict[int, List[str]]:
      """
      Obtém todos os arquivos na rede

      Returns:
          Dicionário com peer_id como chave e lista de arquivos como valor
      """
      if self.is_tracker:

          if not hasattr(self, 'file_index'):
              self.file_index = {}
          return {peer_id: list(files) for peer_id, files in self.file_index.items()}


      if not self.tracker_proxy:
          self.logger.error("Tracker não encontrado")
          return {}

      try:

          name_server = Pyro5.api.locate_ns()
          trackers = [name for name in name_server.list().keys() if name.startswith("Tracker_Epoca_")]

          if not trackers:
              self.logger.error("Nenhum tracker registrado")
              return {}


          max_epoch = max([int(t.split("_")[-1]) for t in trackers])
          tracker_name = f"Tracker_Epoca_{max_epoch}"
          tracker_uri = name_server.lookup(tracker_name)


          tracker_proxy = Pyro5.api.Proxy(tracker_uri)

          return tracker_proxy.get_file_index()
      except Exception as e:
          self.logger.error(f"Erro ao obter índice de arquivos: {e}")
          return {}

    @Pyro5.api.expose
    def get_file_index(self) -> Dict[int, List[str]]:
        """
        [Função do Tracker] Retorna o índice completo de arquivos

        Returns:
            Dicionário com peer_id como chave e lista de arquivos como valor
        """
        if not self.is_tracker:
            return {}


        if not hasattr(self, 'file_index'):
            self.file_index = {}

        return {peer_id: list(files) for peer_id, files in self.file_index.items()}
