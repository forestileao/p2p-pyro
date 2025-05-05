#!/usr/bin/env python3
"""
Script para criar arquivos de exemplo para cada peer
Isso facilita o teste da aplicação, gerando arquivos de diferentes tamanhos
para cada peer, permitindo testar o compartilhamento e transferência.
"""

import os
import random
import string
import argparse

def generate_random_content(size_kb):
    """Gera conteúdo aleatório com tamanho aproximado em KB"""
    # Converter KB para bytes
    size_bytes = size_kb * 1024

    # Gerar conteúdo aleatório
    content = ''.join(random.choices(string.ascii_letters + string.digits, k=size_bytes))
    return content.encode('utf-8')

def create_files_for_peer(peer_id, num_files=5, min_size_kb=1, max_size_kb=100):
    """Cria arquivos de exemplo para um peer"""
    # Diretório do peer
    peer_dir = os.path.join("files", f"peer_{peer_id}")
    os.makedirs(peer_dir, exist_ok=True)

    print(f"Criando {num_files} arquivos para o peer {peer_id}...")

    # Criar arquivos
    for i in range(1, num_files + 1):
        # Tamanho aleatório entre min_size_kb e max_size_kb
        size_kb = random.randint(min_size_kb, max_size_kb)

        # Nome do arquivo com peer_id para evitar duplicação entre peers
        filename = f"arquivo_peer{peer_id}_{i}.txt"
        file_path = os.path.join(peer_dir, filename)

        # Gerar e salvar conteúdo
        content = generate_random_content(size_kb)
        with open(file_path, "wb") as f:
            f.write(content)

        print(f"  Criado: {filename} ({size_kb} KB)")

def create_common_files(num_files=3, min_size_kb=1, max_size_kb=100, peer_ids=None):
    """Cria arquivos comuns que serão compartilhados entre alguns peers"""
    if peer_ids is None or len(peer_ids) < 2:
        print("É necessário especificar pelo menos 2 peers para arquivos comuns.")
        return

    print(f"Criando {num_files} arquivos comuns para os peers {peer_ids}...")

    # Criar arquivos
    for i in range(1, num_files + 1):
        # Tamanho aleatório
        size_kb = random.randint(min_size_kb, max_size_kb)

        # Nome do arquivo
        filename = f"arquivo_comum_{i}.txt"

        # Gerar conteúdo (o mesmo para todos os peers)
        content = generate_random_content(size_kb)

        # Salvar em cada peer especificado
        for peer_id in peer_ids:
            peer_dir = os.path.join("files", f"peer_{peer_id}")
            os.makedirs(peer_dir, exist_ok=True)

            file_path = os.path.join(peer_dir, filename)
            with open(file_path, "wb") as f:
                f.write(content)

            print(f"  Copiado: {filename} ({size_kb} KB) para peer {peer_id}")

def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description="Cria arquivos de exemplo para os peers")
    parser.add_argument("--peers", type=int, default=5, help="Número de peers (padrão: 5)")
    parser.add_argument("--files", type=int, default=5, help="Número de arquivos por peer (padrão: 5)")
    parser.add_argument("--common", type=int, default=3, help="Número de arquivos comuns (padrão: 3)")
    parser.add_argument("--min-size", type=int, default=1, help="Tamanho mínimo em KB (padrão: 1)")
    parser.add_argument("--max-size", type=int, default=100, help="Tamanho máximo em KB (padrão: 100)")
    args = parser.parse_args()

    # Criar diretório base
    os.makedirs("files", exist_ok=True)

    # Criar arquivos exclusivos para cada peer
    for peer_id in range(1, args.peers + 1):
        create_files_for_peer(peer_id, args.files, args.min_size, args.max_size)

    # Criar alguns arquivos comuns (compartilhados entre alguns peers)
    if args.common > 0:
        # Escolher aleatoriamente alguns peers para compartilhar arquivos
        if args.peers >= 3:
            # Escolher um subconjunto aleatório de peers
            num_sharing_peers = min(args.peers, max(2, args.peers // 2))
            sharing_peers = random.sample(range(1, args.peers + 1), num_sharing_peers)
        else:
            # Se houver poucos peers, compartilhar entre todos
            sharing_peers = list(range(1, args.peers + 1))

        create_common_files(args.common, args.min_size, args.max_size, sharing_peers)

    print("\nArquivos de exemplo criados com sucesso!")

if __name__ == "__main__":
    main()
