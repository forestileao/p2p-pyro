import sys
import os
import time
import threading
import argparse
import Pyro5.api
import Pyro5.nameserver
import subprocess
from typing import List

def start_nameserver():
    """Inicia o serviço de nomes do PyRO"""
    print("Iniciando o serviço de nomes (binder) PyRO...")


    try:
        ns = Pyro5.api.locate_ns()
        print(f"Serviço de nomes já está rodando em {ns._pyroUri}")
        return None
    except Exception:
        pass


    ns_proc = subprocess.Popen(
        [sys.executable, "-m", "Pyro5.nameserver", "--host=localhost"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )


    for i in range(10):
        try:
            time.sleep(0.5)
            ns = Pyro5.api.locate_ns()
            print(f"Serviço de nomes iniciado em {ns._pyroUri}")
            return ns_proc
        except Exception:
            continue

    print("Falha ao iniciar o serviço de nomes.")
    if ns_proc:
        ns_proc.terminate()
    return None

def start_peer(peer_id, files_dir=None):
    """Inicia um peer"""
    print(f"Iniciando peer {peer_id}...")

    from gui import PeerGUI


    if not files_dir:
        files_dir = os.path.join("files", f"peer_{peer_id}")


    os.makedirs(files_dir, exist_ok=True)


    peer_gui = PeerGUI(peer_id, files_dir)
    peer_gui.run()

def start_all_peers(num_peers=5, nameserver=True):
    """Inicia o serviço de nomes e todos os peers"""
    ns_proc = None


    if nameserver:
        ns_proc = start_nameserver()
        if not ns_proc:
            print("Falha ao iniciar serviço de nomes. Verifique se já há um serviço rodando.")

            try:
                ns = Pyro5.api.locate_ns()
                print(f"Conectado a serviço de nomes existente em {ns._pyroUri}")
            except Exception:
                print("Não foi possível conectar a um serviço de nomes. Encerrando.")
                return


    os.makedirs("files", exist_ok=True)


    peer_processes = []
    for i in range(1, num_peers + 1):
        peer_proc = subprocess.Popen(
            [sys.executable, __file__, "--peer", str(i)],


        )
        peer_processes.append(peer_proc)
        time.sleep(1)


    try:
        for proc in peer_processes:
            proc.wait()
    except KeyboardInterrupt:
        print("Interrompendo todos os processos...")
        for proc in peer_processes:
            proc.kill()
        if ns_proc:
            ns_proc.kill()

def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description="Aplicação P2P com eleição de tracker")


    subparsers = parser.add_subparsers(dest="mode", help="Modo de operação")


    all_parser = subparsers.add_parser("all", help="Iniciar todos os componentes")
    all_parser.add_argument("--peers", type=int, default=5, help="Número de peers para iniciar")
    all_parser.add_argument("--no-nameserver", action="store_true", help="Não iniciar serviço de nomes (assume que já está rodando)")


    ns_parser = subparsers.add_parser("nameserver", help="Iniciar apenas o serviço de nomes")


    peer_parser = subparsers.add_parser("peer", help="Iniciar um peer individual")
    peer_parser.add_argument("--peer", type=int, required=True, help="ID do peer")
    peer_parser.add_argument("--files-dir", type=str, help="Diretório para armazenar arquivos")


    parser.add_argument("--peer", type=int, help=argparse.SUPPRESS)
    parser.add_argument("--files-dir", type=str, help=argparse.SUPPRESS)

    args = parser.parse_args()


    if args.peer:

        start_peer(args.peer, args.files_dir)
    elif args.mode == "all":

        start_all_peers(args.peers, not args.no_nameserver)
    elif args.mode == "nameserver":

        ns_proc = start_nameserver()
        if ns_proc:
            try:
                print("Serviço de nomes rodando. Pressione Ctrl+C para encerrar.")
                ns_proc.wait()
            except KeyboardInterrupt:
                ns_proc.kill()
                print("Serviço de nomes encerrado.")
    elif args.mode == "peer":

        start_peer(args.peer, args.files_dir)
    else:

        parser.print_help()

if __name__ == "__main__":
    main()
