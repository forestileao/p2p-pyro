import os
import sys
import subprocess
import argparse
import time

def setup_environment():

    os.makedirs("files", exist_ok=True)


    try:
        import Pyro5
    except ImportError:
        print("Instalando dependência: Pyro5...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "Pyro5"])

def start_nameserver():
    print("Iniciando o serviço de nomes (binder) PyRO...")


    ns_proc = subprocess.Popen(
        [sys.executable, "-m", "Pyro5.nameserver", "--host=localhost"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )


    time.sleep(2)
    print("Serviço de nomes iniciado.")

    return ns_proc

def start_peers(num_peers=5, delay=1):
    print(f"Iniciando {num_peers} peers...")

    peer_processes = []
    for i in range(1, num_peers + 1):
        print(f"Iniciando peer {i}...")

        peer_proc = subprocess.Popen(
            [sys.executable, "main.py", "--peer", str(i)],
        )
        peer_processes.append(peer_proc)

        if peer_proc.poll() is not None:
            print(f"ERRO: Peer {i} falhou ao iniciar!")
        time.sleep(delay)

    return peer_processes

def main():
    parser = argparse.ArgumentParser(description="Executa a aplicação P2P com eleição de tracker")
    parser.add_argument("--peers", type=int, default=5, help="Número de peers a iniciar (padrão: 5)")
    parser.add_argument("--no-nameserver", action="store_true", help="Não iniciar o serviço de nomes (já deve estar rodando)")
    args = parser.parse_args()


    setup_environment()


    ns_proc = None
    if not args.no_nameserver:
        ns_proc = start_nameserver()


    peer_processes = start_peers(args.peers)


    try:
        print("\nSistema P2P iniciado com sucesso!")
        print("Pressione Ctrl+C para encerrar todos os processos.")


        for proc in peer_processes:
            proc.wait()

    except KeyboardInterrupt:
        print("\nEncerrando aplicação...")


        for proc in peer_processes:
            proc.terminate()

        if ns_proc:
            ns_proc.terminate()

        print("Aplicação encerrada.")

if __name__ == "__main__":
    main()
