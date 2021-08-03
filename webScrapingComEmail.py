# salva no banco de dados, títulos e links de artigos da wikipédia, e quando finaliza, apenas ao interromper mesmo o programa, envia um e-mail informando que terminou
# os artigos serão buscados em idioma português brasileiro, pois, é mais de boa!
from urllib.request import urlopen
from urllib.error import HTTPError
from urllib.error import URLError
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from colorama import Fore
from datetime import datetime
from pymysql import cursors
import re 
import pymysql
import getpass
import random
import smtplib
import requests
import socket
import sys
from requests.api import get

    
def bd():
    """Salva no banco de dados"""
    # nome do banco de dados: wiki, nome da tabela: tabela
    senha = getpass.getpass(Fore.LIGHTWHITE_EX + 'Informe a senha para conectar-se ao banco de dados: ')
    nome_banco: str = str(input('Digite o nome do banco de dados: '))
    conexao = pymysql.connect(host='127.0.0.1',user='root', password=senha, database=nome_banco)
    print(f"Conectado ao banco de dados {nome_banco} versão {conexao.get_server_info()}")
    cursor = conexao.cursor()
    cursor.execute('SELECT DATABASE();')
    return cursor


def sendEmail(meuemail, emaildestino, senha, msg='Programa Iniciado'):
    """Envia os e-mails pontuando prováveis efeitos"""
    server = 'smtp-mail.outlook.com'
    port = 587
    bind = smtplib.SMTP(server, port)

    # login:
    bind.ehlo()
    bind.starttls()  # criptografia
    bind.login(meuemail, senha)
    # dados:
    enviar_msg = MIMEMultipart()
    enviar_msg['Subject'] = 'Controle Bot Crawler'
    enviar_msg['From'] = meuemail
    enviar_msg['To'] = emaildestino
    enviar_msg.attach(MIMEText(msg, 'plain'))
    print('Enviando mensagem...')
    return bind.sendmail(enviar_msg['From'], enviar_msg['To'], enviar_msg.as_string()), 'Enviado'


class ParserHTML:
    """Parser do html requisitado através do protocolo HTTP"""
    def parser(self, url):
        global emailMe
        global emailTo
        global senha
        
        try:
            html = urlopen(url)
        except HTTPError:
            print(Fore.LIGHTRED_EX + 'Falhou em uma primeira tentativa, provavelmente, pela página estar ausente ou problema no servidor\nErros possíveis 404 ou 500...')
            try:
                req = requests(url)
            except requests.RequestException:
                print(Fore.LIGHTRED_EX + 'Erro também na segunda tentativa')
                sendEmail(emailMe, emailTo, senha, f"Ocorreu um erro de requisição Nome pc: {getpass.getuser()}\nSO: {sys.platform}\nIP interno{socket.gethostbyname(socket.gethostname())}\nIP externo: {requests.get('https://api.ipify.org').text}")
            else:
                return BeautifulSoup(req, 'html.parser')
        except URLError:
            print(Fore.LIGHTRED_EX + 'Url error\nAguarde e tente novamente')
        else:
            return BeautifulSoup(html.read(), 'html.parser')


class WebCrawler:
    """Acessa cada url e pega o título da página"""
    def crawler(self, url, tagTitulo, tagLinks, bd):
        lista_links = []
        beauty = ParserHTML()
        dominio_principal = 'https://pt.wikipedia.org'

        objetoBeauty = beauty.parser(url) 
        titulos = objetoBeauty.select(tagTitulo) # captura o título da página, após acessá-la
        for titulo in titulos:
            print(Fore.LIGHTYELLOW_EX + f"Artigo: {titulo.text} : Link: {url}")
            # salva no banco de dados:
            bd.execute(f"INSERT INTO tabela (Título, Links) VALUES {(titulo.text, url)}")
            bd.connection.commit()
            print('salvo no DB wiki')
            print()

        links = objetoBeauty.find_all(tagLinks, href=re.compile("^(/wiki/)((?!:).)*$")) # expressão para pegar apenas artigos
        # armazena os links na lista:
        for link in links:
            if 'href' in link.attrs:
                lista_links.append(urlparse(dominio_principal).scheme + ':' + '//' + urlparse(dominio_principal).netloc + link.attrs['href']) 
        #busca os links encontrados de forma aleatória:
        newCrawler = WebCrawler()     
        try:  
            return newCrawler.crawler(lista_links[random.randint(0, len(lista_links) - 1)], tagTitulo, tagLinks, bd)
        except IndexError:
            # enviar email
            print(Fore.RED + 'Erro de index, retornando...')
            return newCrawler.crawler(url, tagTitulo, tagLinks, bd)


if __name__ == '__main__':
    # lista passada com informações de url, tags html para identificação dos conteúdos
    linkInicio = ['https://pt.wikipedia.org/wiki/Python', 'h1', 'a']
    emailMe: str = str(input("Informe o seu e-mail: "))
    emailTo: str = str(input("Informe o destinatário: "))
    senha = getpass.getpass('Informe a senha para acesso ao e-mail: ')
    sendEmail(emailMe, emailTo, senha)
    try:
        bancoDados = bd()
        print(Fore.BLUE + 'Iniciando rastreamento da wiki!')
        print(Fore.GREEN + 'Aperte os cintos :)')
        botCrawler = WebCrawler()
        botCrawler.crawler(linkInicio[0], linkInicio[1], linkInicio[2], bancoDados)
    except KeyboardInterrupt:
        # bye
        bancoDados.close()
        print('Encerrando conexão com banco de dados')
        msg = f"O programa foi finalizado. Nome pc: {getpass.getuser()}\nSO: {sys.platform}\nIP interno{socket.gethostbyname(socket.gethostname())}\nIP externo: {requests.get('https://api.ipify.org').text}"
        sendEmail(emailMe, emailTo, senha, msg)
        print(Fore.MAGENTA + '\nBye!')
