import os
import zipfile
import tempfile
import shutil
import hashlib
import platform
import re 
import time
import psutil
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
from typing import Optional, List
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
import json

class FileServerBot:
    def __init__(self, token: str, allowed_users: Optional[List[int]] = None):
        self.token = token
        self.allowed_users = allowed_users or []
        self.current_dir = os.getcwd()
        self.temp_dir = tempfile.gettempdir()
        self.max_file_size = 50 * 1024 * 1024  # 50MB
        self.setup_logging()
        self.load_bookmarks()
        
    def setup_logging(self):
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger('FileServerBot')
        self.logger.setLevel(logging.INFO)
        file_handler = logging.handlers.RotatingFileHandler(
            'logs/bot.log',
            maxBytes=1024*1024,  # 1MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        
        error_handler = logging.handlers.RotatingFileHandler(
            'logs/error.log',
            maxBytes=1024*1024,
            backupCount=5,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s\n%(exc_info)s'
        ))
        
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        ))
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(error_handler)
        self.logger.addHandler(console_handler)

    def load_bookmarks(self):
        self.bookmarks_file = Path("bookmarks.json")
        if self.bookmarks_file.exists():
            with open(self.bookmarks_file, 'r') as f:
                self.bookmarks = json.load(f)
        else:
            self.bookmarks = {}
            self.save_bookmarks()

    def save_bookmarks(self):
        with open(self.bookmarks_file, 'w') as f:
            json.dump(self.bookmarks, f, indent=4)

    async def check_auth(self, update: Update) -> bool:
        user_id = update.effective_user.id
        if self.allowed_users and user_id not in self.allowed_users:
            await update.message.reply_text("⛔ Acesso negado. Você não está autorizado.")
            self.logger.warning(f"Tentativa de acesso não autorizado do usuário {user_id}")
            return False
        return True

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update):
            return

        commands = """
🤖 *Comandos disponíveis:*

📁 *Navegação*
/ls - Lista arquivos do diretório atual
/cd <pasta> - Muda para a pasta especificada
/up - Volta um nível no diretório
/pwd - Mostra diretório atual
/tree [profundidade] - Mostra árvore de diretórios

📥 *Download*
/get <arquivo> - Baixa um arquivo
/getzip <arquivo/pasta> - Baixa compactado em ZIP
/cat <arquivo> - Mostra conteúdo de arquivo texto
/tail <arquivo> [linhas] - Mostra últimas linhas de um arquivo
/find <termo> - Busca arquivos por nome
/search <texto> - Busca texto dentro dos arquivos

🔖 *Favoritos*
/bookmark add <nome> - Adiciona diretório atual aos favoritos
/bookmark list - Lista favoritos
/bookmark go <nome> - Vai para o favorito
/bookmark del <nome> - Remove favorito

⚙️ *Sistema*
/disk - Mostra espaço em disco
/sys - Mostra informações do sistema
/processes - Lista processos em execução
/kill <pid> - Finaliza um processo
/logs - Download dos arquivos de log

💾 *Operações*
/mkdir <nome> - Cria diretório
/rm <arquivo/pasta> - Remove arquivo ou pasta
/cp <origem> <destino> - Copia arquivo ou pasta
/mv <origem> <destino> - Move arquivo ou pasta
/rename <antigo> <novo> - Renomeia arquivo ou pasta
/chmod <permissões> <arquivo> - Altera permissões
/hash <arquivo> - Calcula hash MD5/SHA256
"""
        await update.message.reply_text(commands, parse_mode='Markdown')
        self.logger.info(f"Comando /start executado por {update.effective_user.id}")

    async def list_directory(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update):
            return

        try:
            items = []
            total_size = 0

            for item in os.listdir(self.current_dir):
                full_path = os.path.join(self.current_dir, item)
                size = 0

                try:
                    if os.path.isfile(full_path):
                        size = os.path.getsize(full_path)
                        total_size += size
                        modified = datetime.fromtimestamp(os.path.getmtime(full_path))
                        safe_name = self.escape_markdown(item)
                        items.append({
                            'type': 'file',
                            'name': item,
                            'size': size,
                            'modified': modified,
                            'display': f"📄 {safe_name} ({self.format_size(size)}) - {modified.strftime('%Y-%m-%d %H:%M')}"
                        })
                    else:
                        safe_name = self.escape_markdown(item)
                        items.append({
                            'type': 'dir',
                            'name': item,
                            'display': f"📁 {safe_name}/"
                        })
                except (PermissionError, FileNotFoundError) as e:
                    safe_name = self.escape_markdown(item)
                    items.append({
                        'type': 'error',
                        'name': item,
                        'display': f"⚠️ {safe_name} (Erro: {str(e)})"
                    })

            items.sort(key=lambda x: (x['type'] != 'dir', x['name'].lower()))

            message = f"📂 *Diretório atual:*\n`{self.current_dir}`\n\n"
            for item in items:
                message += item['display'] + "\n"

            message += f"\n📊 Total: {len(items)} items ({self.format_size(total_size)})"

            if len(message) > 4000:
                for i in range(0, len(message), 4000):
                    await update.message.reply_text(message[i:i + 4000], parse_mode='Markdown')
            else:
                await update.message.reply_text(message, parse_mode='Markdown')

            self.logger.info(f"Listagem do diretório {self.current_dir} executada por {update.effective_user.id}")

        except Exception as e:
            error_msg = f"❌ Erro ao listar diretório: {str(e)}"
            await update.message.reply_text(error_msg)
            self.logger.error(f"Erro na listagem: {str(e)}", exc_info=True)

    def escape_markdown(self, text):
        special_characters = r'[_*`|]'
        return re.sub(r'([_`|*])', r'\\\1', text)

    async def print_working_directory(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update):
            return
            
        try:
            absolute_path = os.path.abspath(self.current_dir)
            
            message = (
                "*📂 Diretório Atual:*\n"
                f"`{absolute_path}`\n\n"
                f"*Diretório Base:* `{os.path.basename(absolute_path)}`\n"
                f"*Parent:* `{os.path.dirname(absolute_path)}`"
            )
            
            await update.message.reply_text(
                message,
                parse_mode='Markdown'
            )
            
            self.logger.info(f"PWD executado por {update.effective_user.id}: {absolute_path}")
            
        except Exception as e:
            error_msg = f"❌ Erro ao mostrar diretório atual: {str(e)}"
            await update.message.reply_text(error_msg)
            self.logger.error(f"Erro no comando PWD: {str(e)}", exc_info=True)

    async def up_directory(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update):
            return

        try:
            parent_path = Path(self.current_dir).parent

            if os.path.exists(parent_path) and os.access(parent_path, os.R_OK):
                self.current_dir = str(parent_path)
                current_dir_name = os.path.basename(self.current_dir) or self.current_dir

                message = (
                    f"⬆️ *Subiu um nível*:\n"
                    f"📂 *Diretório atual*: `{self.current_dir}`\n\n"
                    f"✨ Diretório anterior: `{str(Path(self.current_dir).parent)}`\n"
                    f"📅 Última modificação: `{datetime.fromtimestamp(os.path.getmtime(self.current_dir)).strftime('%Y-%m-%d %H:%M')}`"
                )
                await update.message.reply_text(message, parse_mode='Markdown')

                self.logger.info(f"Usuário {update.effective_user.id} subiu para o diretório: {self.current_dir}")

            else:
                error_message = "❌ Não é possível subir mais (sem permissão ou no diretório raiz)"
                await update.message.reply_text(error_message)

                self.logger.warning(f"Usuário {update.effective_user.id} tentou subir para {parent_path}, mas não foi possível.")

        except Exception as e:
            error_msg = f"❌ Ocorreu um erro ao tentar subir o diretório: {str(e)}"
            await update.message.reply_text(error_msg, parse_mode='Markdown')
            self.logger.error(f"Erro ao subir diretório: {str(e)}", exc_info=True)

    async def tree(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update):
            return
            
        try:
            max_depth = 3  # default depth
            if context.args:
                try:
                    max_depth = int(context.args[0])
                except ValueError:
                    await update.message.reply_text("❌ Profundidade deve ser um número")
                    return
            
            result = ["📂 " + self.current_dir]
            
            def add_tree(path: Path, prefix: str = "", depth: int = 1):
                if depth > max_depth:
                    return
                    
                paths = sorted(path.glob("*"))
                for i, p in enumerate(paths):
                    is_last = i == len(paths) - 1
                    result.append(prefix + ("└── " if is_last else "├── ") + (
                        "📁 " if p.is_dir() else "📄 ") + p.name)
                    if p.is_dir():
                        add_tree(p, prefix + ("    " if is_last else "│   "), depth + 1)
            
            add_tree(Path(self.current_dir))
            
            tree_text = "\n".join(result)
            if len(tree_text) > 4000:
                for i in range(0, len(tree_text), 4000):
                    await update.message.reply_text(tree_text[i:i+4000])
            else:
                await update.message.reply_text(tree_text)
                
            self.logger.info(f"Árvore de diretórios gerada por {update.effective_user.id}")
            
        except Exception as e:
            error_msg = f"❌ Erro ao gerar árvore: {str(e)}"
            await update.message.reply_text(error_msg)
            self.logger.error(f"Erro na geração da árvore: {str(e)}", exc_info=True)

    async def change_directory(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update):
            return
            
        try:
            if not context.args:
                await update.message.reply_text("❌ Uso: /cd <pasta>")
                return
                
            path = " ".join(context.args)
            
            if path == "..":
                new_path = str(Path(self.current_dir).parent)
            elif path == "~" or path == "$HOME":
                new_path = str(Path.home())
            elif path.startswith("/") or (platform.system() == "Windows" and path[1:3] == ":\\"): 
                new_path = path
            else:
                new_path = os.path.join(self.current_dir, path)
                
            new_path = os.path.abspath(new_path)
            
            if not os.path.exists(new_path):
                await update.message.reply_text("❌ Diretório não existe")
                return
                
            if not os.path.isdir(new_path):
                await update.message.reply_text("❌ O caminho especificado não é um diretório")
                return
                
            try:
                os.listdir(new_path)
            except PermissionError:
                await update.message.reply_text("❌ Sem permissão de acesso ao diretório")
                return
                
            self.current_dir = new_path
            
            items = os.listdir(self.current_dir)
            dirs = sum(1 for item in items if os.path.isdir(os.path.join(self.current_dir, item)))
            files = len(items) - dirs
            
            message = f"✅ Mudou para: `{self.current_dir}`\n"
            message += f"📊 {dirs} pastas, {files} arquivos"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            self.logger.info(f"Diretório alterado para {self.current_dir} por {update.effective_user.id}")
            
        except Exception as e:
            error_msg = f"❌ Erro ao mudar diretório: {str(e)}"
            await update.message.reply_text(error_msg)
            self.logger.error(f"Erro ao mudar diretório: {str(e)}", exc_info=True)
        
    async def bookmark_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update):
            return
            
        if not context.args:
            await update.message.reply_text("❌ Uso: /bookmark <add|list|go|del> [nome]")
            return
            
        action = context.args[0].lower()
        
        try:
            if action == "add":
                if len(context.args) < 2:
                    await update.message.reply_text("❌ Especifique um nome para o favorito")
                    return
                name = context.args[1]
                self.bookmarks[name] = self.current_dir
                self.save_bookmarks()
                await update.message.reply_text(f"✅ Favorito '{name}' adicionado")
                
            elif action == "list":
                if not self.bookmarks:
                    await update.message.reply_text("📑 Nenhum favorito salvo")
                    return
                message = "📑 *Favoritos:*\n\n"
                for name, path in self.bookmarks.items():
                    message += f"• *{name}*: `{path}`\n"
                await update.message.reply_text(message, parse_mode='Markdown')
                
            elif action == "go":
                if len(context.args) < 2:
                    await update.message.reply_text("❌ Especifique o nome do favorito")
                    return
                name = context.args[1]
                if name not in self.bookmarks:
                    await update.message.reply_text("❌ Favorito não encontrado")
                    return
                if os.path.exists(self.bookmarks[name]):
                    self.current_dir = self.bookmarks[name]
                    await update.message.reply_text(f"✅ Mudou para: {self.current_dir}")
                else:
                    await update.message.reply_text("❌ Diretório do favorito não existe mais")
                    
            elif action == "del":
                if len(context.args) < 2:
                    await update.message.reply_text("❌ Especifique o nome do favorito")
                    return
                name = context.args[1]
                if name in self.bookmarks:
                    del self.bookmarks[name]
                    self.save_bookmarks()
                    await update.message.reply_text(f"✅ Favorito '{name}' removido")
                else:
                    await update.message.reply_text("❌ Favorito não encontrado")
                    
            else:
                await update.message.reply_text("❌ Ação inválida. Use: add, list, go ou del")
                
        except Exception as e:
            error_msg = f"❌ Erro ao gerenciar favoritos: {str(e)}"
            await update.message.reply_text(error_msg)
            self.logger.error(f"Erro nos favoritos: {str(e)}", exc_info=True)

    async def disk_space(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update):
            return
            
        try:
            message = "💾 *Informações de Disco:*\n\n"
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    message += f"*Partição:* `{partition.mountpoint}`\n"
                    message += f"• Total: {self.format_size(usage.total)}\n"
                    message += f"• Usado: {self.format_size(usage.used)} ({usage.percent}%)\n"
                    message += f"• Livre: {self.format_size(usage.free)}\n\n"
                except PermissionError:
                    continue
                    
            await update.message.reply_text(message, parse_mode='Markdown')
            self.logger.info(f"Informações de disco consultadas por {update.effective_user.id}")
            
        except Exception as e:
            error_msg = f"❌ Erro ao obter informações de disco: {str(e)}"
            await update.message.reply_text(error_msg)
            self.logger.error(f"Erro na consulta de disco: {str(e)}", exc_info=True)


    async def system_info(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update):
            return

        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            boot_time = datetime.fromtimestamp(psutil.boot_time())

            message = "*💻 Informações do Sistema:* \n\n"
            message += f"⚙️ *Processador:* `{platform.processor()}`\n"
            message += f"📊 *Uso de CPU:* `{cpu_percent}%`\n"
            message += f"🧠 *Memória Total:* `{self.format_size(memory.total)}`\n"
            message += f"💾 *Memória Usada:* `{self.format_size(memory.used)} ({memory.percent}%)`\n"
            message += f"🆓 *Memória Livre:* `{self.format_size(memory.available)}`\n"
            message += f"⏳ *Tempo Ligado:* `{str(datetime.now() - boot_time).split('.')[0]}`\n"  

            await update.message.reply_text(message, parse_mode='Markdown')
            self.logger.info(f"Informações do sistema consultadas por {update.effective_user.id}")

        except Exception as e:
            error_msg = f"❌ Erro ao obter informações do sistema: {str(e)}"
            await update.message.reply_text(error_msg, parse_mode='Markdown')
            self.logger.error(f"Erro na consulta do sistema: {str(e)}", exc_info=True)


    async def get_zip(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update):
            return

        if len(context.args) < 1:
            await update.message.reply_text("❌ Uso: /getzip <pasta>")
            return

        try:
            folder_name = context.args[0]
            folder_path = os.path.join(self.current_dir, folder_name)

            if not os.path.exists(folder_path):
                await update.message.reply_text("❌ Pasta não encontrada")
                return

            zip_filename = f"{folder_name}.zip"
            zip_path = os.path.join(self.current_dir, zip_filename)
            status_message = await update.message.reply_text("🔨 Empacotando arquivo...")

            start_time = time.time()  

            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as zipf:
                for root, dirs, files in os.walk(folder_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        zipf.write(file_path, os.path.relpath(file_path, folder_path))

            elapsed_time = time.time() - start_time
            await status_message.edit_text(f"✅ Arquivo compactado em {elapsed_time:.2f} segundos. Enviando...")

            with open(zip_path, 'rb') as zip_file:
                await update.message.reply_document(
                    document=InputFile(zip_file, filename=zip_filename),
                    caption=f"Arquivo compactado: {zip_filename}"
                )

            os.remove(zip_path)
            await update.message.reply_text(f"📦 Arquivo enviado com sucesso!")

            self.logger.info(f"ZIP {zip_filename} enviado e removido com sucesso por {update.effective_user.id}")

        except Exception as e:
            error_msg = f"❌ Erro ao criar ou enviar o ZIP: {str(e)}"
            await update.message.reply_text(error_msg)
            self.logger.error(f"Erro ao criar ou enviar o ZIP: {str(e)}", exc_info=True)

    async def list_processes(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update):
            return
            
        try:
            message = "⚙️ *Processos em Execução:*\n\n"
            processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    pinfo = proc.info
                    processes.append({
                        'pid': pinfo['pid'],
                        'name': pinfo['name'],
                        'cpu': pinfo['cpu_percent'],
                        'mem': pinfo['memory_percent']
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            processes.sort(key=lambda x: x['cpu'], reverse=True)
            for proc in processes[:20]:
                message += f"*PID:* `{proc['pid']}` - {proc['name']}\n"
                message += f"CPU: {proc['cpu']:.1f}% | MEM: {proc['mem']:.1f}%\n\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            self.logger.info(f"Lista de processos consultada por {update.effective_user.id}")
            
        except Exception as e:
            error_msg = f"❌ Erro ao listar processos: {str(e)}"
            await update.message.reply_text(error_msg)
            self.logger.error(f"Erro na listagem de processos: {str(e)}", exc_info=True)

    async def kill_process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update):
            return
            
        if not context.args:
            await update.message.reply_text("❌ Uso: /kill <PID>")
            return
            
        try:
            pid = int(context.args[0])
            process = psutil.Process(pid)
            process_name = process.name()
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ Sim", callback_data=f"kill_yes_{pid}"),
                    InlineKeyboardButton("❌ Não", callback_data="kill_no")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"⚠️ Tem certeza que deseja finalizar o processo:\n"
                f"PID: {pid}\n"
                f"Nome: {process_name}",
                reply_markup=reply_markup
            )
            
        except ValueError:
            await update.message.reply_text("❌ PID deve ser um número")
        except psutil.NoSuchProcess:
            await update.message.reply_text("❌ Processo não encontrado")
        except Exception as e:
            error_msg = f"❌ Erro ao tentar finalizar processo: {str(e)}"
            await update.message.reply_text(error_msg)
            self.logger.error(f"Erro ao finalizar processo: {str(e)}", exc_info=True)

    async def kill_process_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        if query.data == "kill_no":
            await query.edit_message_text("❌ Operação cancelada")
            return
            
        try:
            pid = int(query.data.split('_')[2])
            process = psutil.Process(pid)
            process_name = process.name()
            process.terminate()
            await query.edit_message_text(f"✅ Processo {process_name} (PID: {pid}) finalizado")
            self.logger.info(f"Processo {pid} finalizado por {update.effective_user.id}")
            
        except Exception as e:
            error_msg = f"❌ Erro ao finalizar processo: {str(e)}"
            await query.edit_message_text(error_msg)
            self.logger.error(f"Erro ao finalizar processo: {str(e)}", exc_info=True)

    async def cat_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update):
            return
            
        if len(context.args) < 1:
            await update.message.reply_text("❌ Uso: /cat <arquivo>")
            return
        
        try:
            filename = " ".join(context.args)
            filepath = os.path.join(self.current_dir, filename)
            
            if not os.path.exists(filepath):
                await update.message.reply_text("❌ Arquivo não encontrado")
                return
            
            if not os.path.isfile(filepath):
                await update.message.reply_text("❌ Não é um arquivo")
                return
            
            with open(filepath, 'r') as f:
                content = f.read(1000)  
                message = f"📄 *Conteúdo de {filename}:*\n\n{content}"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            self.logger.info(f"Conteúdo do arquivo {filename} exibido para {update.effective_user.id}")
        
        except Exception as e:
            error_msg = f"❌ Erro ao exibir conteúdo do arquivo: {str(e)}"
            await update.message.reply_text(error_msg)
            self.logger.error(f"Erro ao exibir conteúdo do arquivo {filename}: {str(e)}", exc_info=True)

    async def tail_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update):
            return
            
        if not context.args:
            await update.message.reply_text("❌ Uso: /tail <arquivo>")
            return
            
        try:
            filename = " ".join(context.args)
            filepath = os.path.join(self.current_dir, filename)
            
            if not os.path.exists(filepath):
                await update.message.reply_text("❌ Arquivo não encontrado")
                return
            
            if not os.path.isfile(filepath):
                await update.message.reply_text("❌ Não é um arquivo")
                return
            
            num_lines = 10
            
            with open(filepath, 'r') as file:
                lines = file.readlines()
                tail = ''.join(lines[-num_lines:]) 
                
            message = f"📄 Últimas {num_lines} linhas de {filename}:\n\n{tail}"
            
            await update.message.reply_text(message)
            self.logger.info(f"Últimas linhas de {filename} exibidas por {update.effective_user.id}")
            
        except Exception as e:
            error_msg = f"❌ Erro ao exibir últimas linhas: {str(e)}"
            await update.message.reply_text(error_msg)
            self.logger.error(f"Erro ao exibir últimas linhas: {str(e)}", exc_info=True)
        
    async def create_directory(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update):
            return
            
        if not context.args:
            await update.message.reply_text("❌ Uso: /mkdir <nome>")
            return
            
        try:
            dirname = " ".join(context.args)
            path = os.path.join(self.current_dir, dirname)
            os.makedirs(path)
            await update.message.reply_text(f"✅ Diretório criado: {dirname}")
            self.logger.info(f"Diretório {dirname} criado por {update.effective_user.id}")
            
        except Exception as e:
            error_msg = f"❌ Erro ao criar diretório: {str(e)}"
            await update.message.reply_text(error_msg)
            self.logger.error(f"Erro ao criar diretório: {str(e)}", exc_info=True)

    async def remove_item(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update):
            return
            
        if not context.args:
            await update.message.reply_text("❌ Uso: /rm <arquivo/pasta>")
            return
            
        try:
            path = " ".join(context.args)
            full_path = os.path.join(self.current_dir, path)
            
            if not os.path.exists(full_path):
                await update.message.reply_text("❌ Arquivo/pasta não existe")
                return
            
            is_dir = os.path.isdir(full_path)
            keyboard = [
                [
                    InlineKeyboardButton("✅ Sim", callback_data=f"rm_yes_{path}"),
                    InlineKeyboardButton("❌ Não", callback_data="rm_no")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"⚠️ Tem certeza que deseja remover {'a pasta' if is_dir else 'o arquivo'}:\n{path}",
                reply_markup=reply_markup
            )
            
        except Exception as e:  
            error_msg = f"❌ Erro ao remover item: {str(e)}"
            await update.message.reply_text(error_msg)
            self.logger.error(f"Erro ao remover item: {str(e)}", exc_info=True)

    async def remove_item_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        if query.data == "rm_no":
            await query.edit_message_text("❌ Operação cancelada")
            return
            
        try:
            path = " ".join(query.data.split('_')[2:])
            full_path = os.path.join(self.current_dir, path)
            
            if os.path.isdir(full_path):
                shutil.rmtree(full_path)
            else:
                os.remove(full_path)
                
            await query.edit_message_text(f"✅ Removido: {path}")
            self.logger.info(f"Item {path} removido por {update.effective_user.id}")
            
        except Exception as e:
            error_msg = f"❌ Erro ao remover: {str(e)}"
            await query.edit_message_text(error_msg)
            self.logger.error(f"Erro ao remover: {str(e)}", exc_info=True)

    async def get_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update):
            return

        if not context.args:
            await update.message.reply_text("❌ Uso: /get <nome_do_arquivo>")
            return

        try:
            filename = " ".join(context.args)
            filepath = os.path.join(self.current_dir, filename)

            if not os.path.exists(filepath):
                await update.message.reply_text("❌ Arquivo não encontrado")
                return

            if not os.path.isfile(filepath):
                await update.message.reply_text("❌ Não é um arquivo válido")
                return

            with open(filepath, 'rb') as file:
                await update.message.reply_document(file)
            
            await update.message.reply_text(f"✅ Arquivo '{filename}' enviado com sucesso")
            self.logger.info(f"Arquivo '{filename}' enviado por {update.effective_user.id}")
            
        except Exception as e:
            error_msg = f"❌ Erro ao enviar arquivo: {str(e)}"
            await update.message.reply_text(error_msg)
            self.logger.error(f"Erro ao enviar arquivo: {str(e)}", exc_info=True)


    async def copy_item(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update):
            return
            
        if len(context.args) < 2:
            await update.message.reply_text("❌ Uso: /cp <origem> <destino>")
            return
            
        try:
            source = context.args[0]
            dest = context.args[1]
            
            source_path = os.path.join(self.current_dir, source)
            dest_path = os.path.join(self.current_dir, dest)
            
            if not os.path.exists(source_path):
                await update.message.reply_text("❌ Arquivo/pasta de origem não existe")
                return
                
            if os.path.isdir(source_path):
                shutil.copytree(source_path, dest_path)
            else:
                shutil.copy2(source_path, dest_path)
                
            await update.message.reply_text(f"✅ Copiado: {source} → {dest}")
            self.logger.info(f"Item {source} copiado para {dest} por {update.effective_user.id}")
            
        except Exception as e:
            error_msg = f"❌ Erro ao copiar: {str(e)}"
            await update.message.reply_text(error_msg)
            self.logger.error(f"Erro ao copiar: {str(e)}", exc_info=True)

    async def move_item(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update):
            return
            
        if len(context.args) < 2:
            await update.message.reply_text("❌ Uso: /mv <origem> <destino>")
            return
            
        try:
            source = context.args[0]
            dest = context.args[1]
            
            source_path = os.path.join(self.current_dir, source)
            dest_path = os.path.join(self.current_dir, dest)
            
            if not os.path.exists(source_path):
                await update.message.reply_text("❌ Arquivo/pasta de origem não existe")
                return
                
            shutil.move(source_path, dest_path)
            await update.message.reply_text(f"✅ Movido: {source} → {dest}")
            self.logger.info(f"Item {source} movido para {dest} por {update.effective_user.id}")
            
        except Exception as e:
            error_msg = f"❌ Erro ao mover: {str(e)}"
            await update.message.reply_text(error_msg)
            self.logger.error(f"Erro ao mover: {str(e)}", exc_info=True)

    async def calculate_hash(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update):
            return
            
        if not context.args:
            await update.message.reply_text("❌ Uso: /hash <arquivo>")
            return
            
        try:
            filename = " ".join(context.args)
            filepath = os.path.join(self.current_dir, filename)
            
            if not os.path.exists(filepath):
                await update.message.reply_text("❌ Arquivo não encontrado")
                return
            
            if not os.path.isfile(filepath):
                await update.message.reply_text("❌ Não é um arquivo")
                return
            
            md5 = hashlib.md5()
            sha256 = hashlib.sha256()
            
            with open(filepath, 'rb') as f:
                while chunk := f.read(8192):
                    md5.update(chunk)
                    sha256.update(chunk)
            
            message = f"🔐 *Hashes para {filename}:*\n\n"
            message += f"*MD5:* `{md5.hexdigest()}`\n"
            message += f"*SHA256:* `{sha256.hexdigest()}`"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            self.logger.info(f"Hash calculado para {filename} por {update.effective_user.id}")
            
        except Exception as e:
            error_msg = f"❌ Erro ao calcular hash: {str(e)}"
            await update.message.reply_text(error_msg)
            self.logger.error(f"Erro ao calcular hash: {str(e)}", exc_info=True)

    async def search_files(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update):
            return
            
        if not context.args:
            await update.message.reply_text("❌ Uso: /find <termo>")
            return
            
        try:
            term = " ".join(context.args).lower()
            results = []
            
            for root, dirs, files in os.walk(self.current_dir):
                for item in dirs + files:
                    if term in item.lower():
                        rel_path = os.path.relpath(os.path.join(root, item), self.current_dir)
                        is_dir = os.path.isdir(os.path.join(root, item))
                        results.append(f"{'📁' if is_dir else '📄'} {rel_path}")
            
            if results:
                message = f"🔍 Resultados para '{term}':\n\n"
                message += "\n".join(results)
            else:
                message = f"❌ Nenhum resultado encontrado para '{term}'"
                
            await update.message.reply_text(message)
            self.logger.info(f"Busca por '{term}' realizada por {update.effective_user.id}")
            
        except Exception as e:
            error_msg = f"❌ Erro na busca: {str(e)}"
            await update.message.reply_text(error_msg)
            self.logger.error(f"Erro na busca: {str(e)}", exc_info=True)

    async def search_content(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not await self.check_auth(update):
                return
                
            if not context.args:
                await update.message.reply_text("❌ Uso: /search <texto>")
                return
                
            try:
                text = " ".join(context.args).lower()
                results = []
                
                text_extensions = {'.txt', '.log', '.py', '.java', '.cpp', '.h', '.c', '.js', '.html', '.css', '.xml', '.json', '.md', '.ini', '.conf'}
                
                for root, _, files in os.walk(self.current_dir):
                    for file in files:
                        if os.path.splitext(file)[1].lower() in text_extensions:
                            full_path = os.path.join(root, file)
                            try:
                                with open(full_path, 'r', encoding='utf-8') as f:
                                    for i, line in enumerate(f, 1):
                                        if text in line.lower():
                                            rel_path = os.path.relpath(full_path, self.current_dir)
                                            results.append(f"📄 {rel_path}:{i}: {line.strip()}")
                            except (UnicodeDecodeError, PermissionError):
                                continue
                
                if results:
                    message = f"🔍 Resultados para '{text}':\n\n"
                    message += "\n\n".join(results[:20])  # Limitar 20 resultados
                    if len(results) > 20:
                        message += f"\n\n... e mais {len(results) - 20} resultados"
                else:
                    message = f"❌ Nenhum resultado encontrado para '{text}'"
                    
                if len(message) > 4000:
                    for i in range(0, len(message), 4000):
                        await update.message.reply_text(message[i:i+4000])
                else:
                    await update.message.reply_text(message)
                    
                self.logger.info(f"Busca de conteúdo por '{text}' realizada por {update.effective_user.id}")
                
            except Exception as e:
                error_msg = f"❌ Erro na busca: {str(e)}"
                await update.message.reply_text(error_msg)
                self.logger.error(f"Erro na busca de conteúdo: {str(e)}", exc_info=True)

    async def show_logs(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not await self.check_auth(update):
            return
            
        try:
            log_dir = Path("logs")
            if not log_dir.exists():
                await update.message.reply_text("❌ Diretório de logs não encontrado")
                return
                
            temp_zip = os.path.join(self.temp_dir, f"logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip")
            
            with zipfile.ZipFile(temp_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for log_file in log_dir.glob("*.log*"):
                    zipf.write(log_file, log_file.name)
            
            with open(temp_zip, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=os.path.basename(temp_zip),
                    caption="📊 Arquivos de log do bot"
                )
            
            os.remove(temp_zip)
            self.logger.info(f"Logs enviados para {update.effective_user.id}")
            
        except Exception as e:
            error_msg = f"❌ Erro ao enviar logs: {str(e)}"
            await update.message.reply_text(error_msg)
            self.logger.error(f"Erro ao enviar logs: {str(e)}", exc_info=True)

    @staticmethod
    def format_size(size):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.1f}{unit}"
            size /= 1024.0
        return f"{size:.1f}PB"

    def run(self):
        app = Application.builder().token(self.token).build()
        
        # Comandos de navegação
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CommandHandler("ls", self.list_directory))
        app.add_handler(CommandHandler("cd", self.change_directory))
        app.add_handler(CommandHandler("up", self.up_directory))
        app.add_handler(CommandHandler("pwd", self.print_working_directory))
        app.add_handler(CommandHandler("tree", self.tree))
        
        # Comandos de download
        app.add_handler(CommandHandler("get", self.get_file))
        app.add_handler(CommandHandler("getzip", self.get_zip))
        app.add_handler(CommandHandler("cat", self.cat_file))
        app.add_handler(CommandHandler("tail", self.tail_file))
        
        # Comandos de busca
        app.add_handler(CommandHandler("find", self.search_files))
        app.add_handler(CommandHandler("search", self.search_content))
        
        # Comandos de favoritos
        app.add_handler(CommandHandler("bookmark", self.bookmark_handler))
        
        # Comandos de sistema
        app.add_handler(CommandHandler("disk", self.disk_space))
        app.add_handler(CommandHandler("sys", self.system_info))
        app.add_handler(CommandHandler("processes", self.list_processes))
        app.add_handler(CommandHandler("kill", self.kill_process))
        app.add_handler(CommandHandler("logs", self.show_logs))
        
        # Comandos de operações com arquivos
        app.add_handler(CommandHandler("mkdir", self.create_directory))
        app.add_handler(CommandHandler("rm", self.remove_item))
        app.add_handler(CommandHandler("cp", self.copy_item))
        app.add_handler(CommandHandler("mv", self.move_item))
        app.add_handler(CommandHandler("hash", self.calculate_hash))
        
        # Handlers de callback para confirmações
        app.add_handler(CallbackQueryHandler(self.kill_process_callback, pattern="^kill_"))
        app.add_handler(CallbackQueryHandler(self.remove_item_callback, pattern="^rm_"))
        
        self.logger.info("Bot iniciado!")
        print("Bot iniciado! Pressione Ctrl+C para parar.")
        app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    TOKEN = ""    
    ALLOWED_USERS = []  # -===== a lista tiver vasia, todos os nego vai poder operar no bot 
    
    bot = FileServerBot(TOKEN, ALLOWED_USERS)
    bot.run()