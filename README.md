# 🚀 **Telegram File Explorer Bot** 🤖
![logo](./images/logo.png)
Bem-vindo ao **Telegram File Explorer Bot**! 🌟 Este bot permite explorar, gerenciar e interagir com seus arquivos de maneira rápida e eficiente diretamente pelo Telegram. 🙌



---
# 🚀 **Tutorial Compacto - Telegram File Explorer Bot** 🤖

## 1. **Clonar o Repositório** 📂

Clone o repositório com o comando:

```bash
git clone https://github.com/lalaio1/telegram-file-explorer.git
cd telegram-file-explorer
```

## 2. **Obter o Token do Bot** 🔑

1. Vá até o [BotFather](https://t.me/BotFather) no Telegram. 
2. Crie um novo bot e obtenha o token seguindo este [tutorial](https://help.zoho.com/portal/en/kb/desk/support-channels/instant-messaging/telegram/articles/telegram-integration-with-zoho-desk#How_to_find_a_token_for_an_existing_Telegram_Bot).

## 3. **Configurar o Token** 📝

1. Abra o arquivo `server.py`.
2. Na linha 1050, adicione seu token entre as aspas:
   ```python
   TOKEN = "seu-token-aqui"
   ```

## 4. **Instalar Dependências** 🔧

Execute o comando para instalar as dependências:

```bash
pip install -r requirements.txt
```

## 5. **Iniciar o Bot** 🚀

- **Linux/macOS**: 
  ```bash
  python3 server.py
  ```

- **Windows**: 
  ```bash
  python server.py
  ```


---

## 🤖 **Comandos Disponíveis**

### 📁 **Navegação**

| Comando      | Descrição                               |
|--------------|-----------------------------------------|
| `/ls`        | Lista arquivos do diretório atual       |
| `/cd <pasta>`| Muda para a pasta especificada         |
| `/up`        | Volta um nível no diretório            |
| `/pwd`       | Mostra o diretório atual               |
| `/tree [profundidade]` | Mostra a árvore de diretórios  |

---

### 📥 **Download**

| Comando            | Descrição                                     |
|--------------------|-----------------------------------------------|
| `/get <arquivo>`   | Baixa um arquivo                             |
| `/getzip <arquivo/pasta>` | Baixa um arquivo ou pasta em formato ZIP |
| `/cat <arquivo>`   | Mostra o conteúdo de um arquivo de texto     |
| `/tail <arquivo> [linhas]` | Mostra as últimas linhas de um arquivo |
| `/find <termo>`    | Busca arquivos por nome                      |
| `/search <texto>`  | Busca texto dentro dos arquivos              |

---

### 🔖 **Favoritos**

| Comando                  | Descrição                                    |
|--------------------------|----------------------------------------------|
| `/bookmark add <nome>`    | Adiciona diretório atual aos favoritos       |
| `/bookmark list`          | Lista os favoritos                          |
| `/bookmark go <nome>`     | Vai para o favorito especificado            |
| `/bookmark del <nome>`    | Remove um favorito                          |

---

### ⚙️ **Sistema**

| Comando            | Descrição                                   |
|--------------------|---------------------------------------------|
| `/disk`            | Mostra o espaço em disco                    |
| `/sys`             | Mostra informações do sistema               |
| `/processes`       | Lista processos em execução                 |
| `/kill <pid>`      | Finaliza um processo                        |
| `/logs`            | Baixa os arquivos de log                    |

---

### 💾 **Operações**

| Comando                | Descrição                                    |
|------------------------|----------------------------------------------|
| `/mkdir <nome>`        | Cria um novo diretório                       |
| `/rm <arquivo/pasta>`  | Remove arquivo ou pasta                      |
| `/cp <origem> <destino>` | Copia arquivo ou pasta                     |
| `/mv <origem> <destino>` | Move arquivo ou pasta                     |
| `/rename <antigo> <novo>` | Renomeia arquivo ou pasta                  |
| `/chmod <permissões> <arquivo>` | Altera permissões de arquivo        |
| `/hash <arquivo>`      | Calcula hash MD5/SHA256 do arquivo          |

---

## 🎨 **Personalização e Estilo**

Este bot é altamente personalizável! Você pode ajustar as configurações do bot, explorar diferentes opções de busca e interação com arquivos e pastas, e muito mais!


📱 **Entre em contato:**

[Entre em contato clicando aqui](https://t.me/lalaio1) ou escaneie o QR code abaixo:  
![1](./images/qrcode.png)

🔗 **Repositório no GitHub:**

- https://github.com/lalaio1/telegram-file-explorer

---

Aqui está o tutorial compacto com emojis para torná-lo mais visual e interativo:

---

## 💬 **Contribuições**

Você pode contribuir para este projeto! Sinta-se à vontade para abrir uma *issue* ou fazer um *pull request* no repositório do GitHub.

🔗 **Repositório**: [Telegram File Explorer no GitHub](https://github.com/lalaio1/telegram-file-explorer)
