#!/usr/bin/env python3
"""
Script para facilitar a execução da aplicação P2P com eleição de tracker
"""

import os
import sys
import subprocess
import argparse
import time

def setup_environment():
    """Prepara o ambiente para execução da aplicação"""
    # Criar diretórios necessários
    os.makedirs("files", exist_ok=True)

    # Verificar dependências
    try:
        import Pyro5
    except ImportError:
        print("Instalando dependência: Pyro5...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "Pyro5"])

def start_nameserver():
    """Inicia o serviço de nomes do PyRO"""
    print("Iniciando o serviço de nomes (binder) PyRO...")

    # Iniciar serviço de nomes em novo processo
    ns_proc = subprocess.Popen(
        [sys.executable, "-m", "Pyro5.nameserver"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    # Aguardar o serviço iniciar
    time.sleep(2)
    print("Serviço de nomes iniciado.")

    return ns_proc

def start_peers(num_peers=5, delay=1):
    """Inicia os processos peer"""
    print(f"Iniciando {num_peers} peers...")

    peer_processes = []
    for i in range(1, num_peers + 1):
        print(f"Iniciando peer {i}...")
        peer_proc = subprocess.Popen(
            [sys.executable, "main.py", "--peer", str(i)]
        )
        peer_processes.append(peer_proc)
        time.sleep(delay)  # Delay para evitar condições de corrida

    return peer_processes

def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description="Executa a aplicação P2P com eleição de tracker")
    parser.add_argument("--peers", type=int, default=5, help="Número de peers a iniciar (padrão: 5)")
    parser.add_argument("--no-nameserver", action="store_true", help="Não iniciar o serviço de nomes (já deve estar rodando)")
    args = parser.parse_args()

    # Preparar ambiente
    setup_environment()

    # Iniciar serviço de nomes se necessário
    ns_proc = None
    if not args.no_nameserver:
        ns_proc = start_nameserver()

    # Iniciar peers
    peer_processes = start_peers(args.peers)

    # Aguardar processos terminarem
    try:
        print("\nSistema P2P iniciado com sucesso!")
        print("Pressione Ctrl+C para encerrar todos os processos.")

        # Aguardar indefinidamente
        for proc in peer_processes:
            proc.wait()

    except KeyboardInterrupt:
        print("\nEncerrando aplicação...")

        # Encerrar todos os processos
        for proc in peer_processes:
            proc.terminate()

        if ns_proc:
            ns_proc.terminate()

        print("Aplicação encerrada.")

if __name__ == "__main__":
    main()
