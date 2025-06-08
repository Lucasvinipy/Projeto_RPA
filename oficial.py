
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging
import os
from datetime import datetime
import json

# Configuração de logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cartorio_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class CartorioScraperOtimizado:
    def __init__(self, arquivo_csv, headless=False):
        self.arquivo_csv = arquivo_csv
        self.headless = headless
        self.driver = None
        self.wait = None
        self.url_base = "https://mapa.onr.org.br"
        self.resultados = []
        
    def setup_driver(self):
        """Configura o driver do Chrome otimizado para velocidade"""
        options = Options()
        
        if self.headless:
            options.add_argument("--headless")
        
        # Otimizações para velocidade - HABILITANDO JavaScript para carregamento correto
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-plugins")
        options.add_argument("--disable-extensions")
        options.add_argument("--window-size=1366,768")
        
        # Anti-detecção básica
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        
        # Configurações de rede - PERMITINDO imagens para carregamento correto do mapa
        prefs = {
            "profile.default_content_setting_values.notifications": 2
        }
        options.add_experimental_option("prefs", prefs)
        
        try:
            self.driver = webdriver.Chrome(options=options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.wait = WebDriverWait(self.driver, 30)  # Aumentei o timeout
            logger.info("Driver configurado com sucesso")
            
        except Exception as e:
            logger.error(f"Erro ao configurar driver: {e}")
            raise
    
    def carregar_csv(self):
        """Carrega o CSV com endereços no formato especificado"""
        try:
            if not os.path.exists(self.arquivo_csv):
                raise FileNotFoundError(f"Arquivo {self.arquivo_csv} não encontrado")
            
            # Detecta o separador do CSV
            with open(self.arquivo_csv, 'r', encoding='utf-8') as f:
                primeira_linha = f.readline()
                
            separador = ';' if ';' in primeira_linha else ','
            logger.info(f"Separador detectado: '{separador}'")
            
            # Lê o CSV com o separador correto
            df = pd.read_csv(self.arquivo_csv, sep=separador)
            logger.info(f"CSV carregado: {len(df)} linhas, Colunas: {df.columns.tolist()}")
            
            # Limpa nomes das colunas (remove espaços)
            df.columns = df.columns.str.strip()
            logger.info(f"Colunas após limpeza: {df.columns.tolist()}")
            
            # Constrói endereço completo baseado nas colunas disponíveis
            enderecos_completos = []
            
            for _, row in df.iterrows():
                partes_endereco = []
                
                # Mapeamento flexível de colunas
                colunas_mapeadas = {
                    'rua': ['rua', 'logradouro', 'endereco', 'address'],
                    'bairro': ['bairro', 'distrito', 'neighborhood'],
                    'cidade': ['cidade', 'city', 'municipio'],
                    'uf': ['uf', 'estado', 'state'],
                    'cep': ['cep', 'postal_code', 'zip'],
                    'pais': ['pais', 'país', 'country']
                }
                
                # Adiciona cada parte do endereço se não for vazia
                for tipo, possiveis_nomes in colunas_mapeadas.items():
                    for nome_col in possiveis_nomes:
                        if nome_col in df.columns and pd.notna(row[nome_col]):
                            valor = str(row[nome_col]).strip()
                            if valor and valor.lower() not in ['nan', 'null', '']:
                                if tipo == 'cep' and len(valor) == 8 and valor.isdigit():
                                    # Formata CEP
                                    valor = f"{valor[:5]}-{valor[5:]}"
                                partes_endereco.append(valor)
                                break  # Só pega a primeira coluna que encontrar
                
                if partes_endereco:
                    endereco_completo = ", ".join(partes_endereco)
                    enderecos_completos.append(endereco_completo)
                else:
                    # Se não conseguiu mapear, tenta usar todas as colunas
                    todas_partes = []
                    for col in df.columns:
                        if pd.notna(row[col]):
                            valor = str(row[col]).strip()
                            if valor and valor.lower() not in ['nan', 'null', '']:
                                todas_partes.append(valor)
                    
                    if todas_partes:
                        endereco_completo = ", ".join(todas_partes)
                        enderecos_completos.append(endereco_completo)
                    else:
                        enderecos_completos.append("")
            
            df['endereco_completo'] = enderecos_completos
            
            # Remove endereços vazios
            df = df[df['endereco_completo'].str.len() > 10]
            
            logger.info(f"Endereços válidos carregados: {len(df)}")
            return df
            
        except Exception as e:
            logger.error(f"Erro ao carregar CSV: {e}")
            raise
    
    def aguardar_mapa_carregado(self):
        """Aguarda o mapa carregar - versão mais robusta"""
        try:
            logger.info("Aguardando carregamento completo da página...")
            
            # 1. Aguarda o DOM básico carregar
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            logger.info("DOM básico carregado")
            
            # 2. Aguarda mais tempo para JavaScript executar
            time.sleep(8)
            
            # 3. Verifica se a página está realmente carregada
            max_tentativas = 6
            for tentativa in range(max_tentativas):
                logger.info(f"Tentativa {tentativa + 1}/{max_tentativas} - Verificando elementos...")
                
                # Verifica múltiplos indicadores de carregamento
                indicadores_carregamento = [
                    # Campos de busca possíveis
                    "input[type='text']",
                    "input[placeholder*='endereço']",
                    "input[placeholder*='Digite']",
                    ".leaflet-control-geocoder",
                    "#geocoder",
                    
                    # Elementos do mapa
                    ".leaflet-container",
                    ".leaflet-map-pane",
                    "canvas",
                    
                    # Botões ou controles
                    "button",
                    ".btn"
                ]
                
                elementos_encontrados = 0
                campo_busca_encontrado = False
                
                for seletor in indicadores_carregamento:
                    try:
                        elementos = self.driver.find_elements(By.CSS_SELECTOR, seletor)
                        if elementos:
                            elementos_encontrados += 1
                            logger.info(f"  ✓ Encontrado: {seletor} ({len(elementos)} elementos)")
                            
                            # Verifica especificamente campos de busca
                            if "input" in seletor:
                                for elem in elementos:
                                    if elem.is_displayed() and elem.is_enabled():
                                        campo_busca_encontrado = True
                                        logger.info(f"  ✓ Campo de busca funcional encontrado!")
                                        break
                    except Exception as e:
                        logger.debug(f"Erro verificando {seletor}: {e}")
                
                logger.info(f"Elementos encontrados: {elementos_encontrados}")
                
                # Se encontrou elementos suficientes, considera carregado
                if elementos_encontrados >= 3:
                    if campo_busca_encontrado:
                        logger.info("✅ Mapa carregado completamente!")
                        return True
                    else:
                        logger.info("Elementos encontrados, mas sem campo de busca funcional")
                
                # Aguarda mais tempo antes da próxima tentativa
                time.sleep(5)
            
            # Última tentativa: verifica qualquer input visível
            logger.info("Última tentativa: procurando qualquer input visível...")
            try:
                inputs = self.driver.find_elements(By.CSS_SELECTOR, "input")
                for inp in inputs:
                    if inp.is_displayed() and inp.size['width'] > 50:
                        logger.info("✅ Input visível encontrado como fallback")
                        return True
            except:
                pass
            
            logger.error("❌ Falha ao detectar carregamento completo do mapa")
            return False
            
        except TimeoutException:
            logger.error("❌ Timeout ao carregar página")
            return False
        except Exception as e:
            logger.error(f"❌ Erro inesperado ao aguardar carregamento: {e}")
            return False
    
    def encontrar_campo_busca(self):
        """Encontra o campo de busca mais provável"""
        seletores = [
            "input[placeholder*='endereço']",
            "input[placeholder*='Digite']",
            "input[placeholder*='Buscar']",
            "input[placeholder*='Search']",
            ".leaflet-control-geocoder input",
            "#geocoder input",
            ".search-input",
            ".address-input",
            "input[type='text']:visible"
        ]
        
        logger.info("Procurando campo de busca...")
        
        for i, seletor in enumerate(seletores):
            try:
                elementos = self.driver.find_elements(By.CSS_SELECTOR, seletor)
                for elemento in elementos:
                    if elemento.is_displayed() and elemento.is_enabled():
                        logger.info(f"✓ Campo encontrado com seletor {i+1}: {seletor}")
                        return elemento
            except Exception as e:
                logger.debug(f"Erro com seletor {seletor}: {e}")
        
        # Fallback: pega o primeiro input visível e grande o suficiente
        try:
            logger.info("Fallback: procurando inputs visíveis...")
            inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
            for inp in inputs:
                if inp.is_displayed() and inp.size['width'] > 100 and inp.size['height'] > 20:
                    logger.info(f"✓ Campo fallback encontrado: width={inp.size['width']}, height={inp.size['height']}")
                    return inp
        except Exception as e:
            logger.error(f"Erro no fallback: {e}")
        
        logger.error("❌ Nenhum campo de busca encontrado")
        return None
    
    def buscar_endereco(self, endereco):
        """Busca um endereço no mapa"""
        try:
            logger.info(f"Buscando: {endereco}")
            
            # Encontra campo de busca
            campo = self.encontrar_campo_busca()
            if not campo:
                return "❌ Campo de busca não encontrado"
            
            # Limpa e digita endereço
            campo.clear()
            time.sleep(1)
            campo.send_keys(endereco)
            time.sleep(1.5)
            campo.send_keys(Keys.ENTER)
            
            # Aguarda resultado com tempo maior
            time.sleep(6)
            
            # Extrai informação do cartório
            info_cartorio = self.extrair_info_cartorio()
            logger.info(f"Resultado: {info_cartorio[:100]}...")
            
            return info_cartorio
            
        except Exception as e:
            erro = f"❌ Erro na busca: {str(e)}"
            logger.error(erro)
            return erro
    
    def extrair_info_cartorio(self):
        """Extrai informações do cartório da página"""
        try:
            # Seletores prioritários para informações de cartório
            seletores_info = [
                ".leaflet-popup-content",
                ".popup-content", 
                "div[style*='background-color: yellow']",
                ".alert-info",
                ".notification"
            ]
            
            # Busca informações
            for seletor in seletores_info:
                try:
                    elementos = self.driver.find_elements(By.CSS_SELECTOR, seletor)
                    for elem in elementos:
                        if elem.is_displayed():
                            texto = elem.text.strip()
                            if texto and len(texto) > 10:
                                # Verifica se contém informação de cartório
                                palavras_chave = ['registro', 'cartório', 'cartorio', 'ri ', 'cnpj', 'imóveis']
                                if any(palavra in texto.lower() for palavra in palavras_chave):
                                    return self.limpar_texto_cartorio(texto)
                except:
                    continue
            
            # Busca por XPath mais específico
            try:
                xpath_cartorio = "//*[contains(text(), 'Registro') or contains(text(), 'Cartório')]"
                elementos = self.driver.find_elements(By.XPATH, xpath_cartorio)
                for elem in elementos:
                    if elem.is_displayed():
                        # Pega o texto do elemento pai que pode ter mais informações
                        parent = elem.find_element(By.XPATH, "..")
                        texto = parent.text.strip()
                        if len(texto) > 10:
                            return self.limpar_texto_cartorio(texto)
            except:
                pass
            
            return "❌ Nenhuma informação de cartório encontrada"
            
        except Exception as e:
            return f"❌ Erro na extração: {str(e)}"
    
    def limpar_texto_cartorio(self, texto):
        """Limpa e formata o texto do cartório"""
        # Remove quebras de linha excessivas
        texto = ' '.join(texto.split())
        
        # Limita o tamanho se muito longo
        if len(texto) > 500:
            texto = texto[:500] + "..."
        
        return texto
    
    def salvar_checkpoint(self, df, indice):
        """Salva checkpoint do progresso"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            arquivo_checkpoint = f"checkpoint_{indice}_{timestamp}.csv"
            
            # Adiciona resultados até o momento
            df_temp = df.copy()
            df_temp['cartorio'] = self.resultados + [''] * (len(df) - len(self.resultados))
            df_temp.to_csv(arquivo_checkpoint, index=False)
            
            logger.info(f"Checkpoint salvo: {arquivo_checkpoint}")
            
        except Exception as e:
            logger.error(f"Erro ao salvar checkpoint: {e}")
    
    def processar_enderecos(self):
        """Processa todos os endereços do CSV"""
        try:
            print("=" * 60)
            print("🏢 PROCESSANDO CARTÓRIOS - ONR")
            print("=" * 60)
            
            # Carrega CSV
            print("📂 Carregando CSV...")
            df = self.carregar_csv()
            
            total = len(df)
            print(f"📊 Total de endereços: {total}")
            
            # Mostra prévia
            print("\n📋 Prévia dos endereços:")
            for i, endereco in enumerate(df['endereco_completo'].head(3), 1):
                print(f"  {i}. {endereco}")
            if total > 3:
                print(f"  ... e mais {total - 3} endereços")
            
            # Confirmação
            resposta = input(f"\n🚀 Processar {total} endereços? (s/n): ")
            if resposta.lower() not in ['s', 'sim']:
                print("❌ Processamento cancelado")
                return None
            
            # Setup do navegador
            print("🔧 Configurando navegador...")
            self.setup_driver()
            
            # Acessa o site
            print(f"🌐 Acessando {self.url_base}...")
            print("⏳ Aguarde, carregamento pode demorar...")
            
            self.driver.get(self.url_base)
            
            if not self.aguardar_mapa_carregado():
                print("❌ Falha ao carregar o mapa")
                print("💡 Tente executar novamente ou verificar sua conexão")
                return None
            
            print("✅ Mapa carregado com sucesso")
            
            # Processa endereços
            print(f"\n🔄 Iniciando processamento...")
            self.resultados = []
            
            for i, (_, row) in enumerate(df.iterrows()):
                endereco = row['endereco_completo']
                
                print(f"\n📍 [{i+1}/{total}] {endereco}")
                
                # Busca informação do cartório
                resultado = self.buscar_endereco(endereco)
                self.resultados.append(resultado)
                
                # Mostra resultado resumido
                resultado_resumido = resultado[:80] + "..." if len(resultado) > 80 else resultado
                print(f"    ✅ {resultado_resumido}")
                
                # Checkpoint a cada 5 endereços
                if (i + 1) % 5 == 0:
                    self.salvar_checkpoint(df, i + 1)
                    print(f"    💾 Checkpoint salvo ({i+1}/{total})")
                
                # Pausa entre buscas
                time.sleep(3)
            
            # Adiciona resultados ao DataFrame
            df['cartorio'] = self.resultados
            
            # Salva resultado final
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            arquivo_final = f"enderecos_cartorios_{timestamp}.csv"
            df.to_csv(arquivo_final, index=False)
            
            # Relatório final
            print("\n" + "=" * 60)
            print("🎉 PROCESSAMENTO CONCLUÍDO!")
            print("=" * 60)
            print(f"📄 Arquivo final: {arquivo_final}")
            
            # Estatísticas
            sucessos = sum(1 for r in self.resultados if not r.startswith("❌"))
            erros = total - sucessos
            
            print(f"📊 Estatísticas:")
            print(f"   • Total processado: {total}")
            print(f"   • Sucessos: {sucessos}")
            print(f"   • Erros: {erros}")
            print(f"   • Taxa de sucesso: {(sucessos/total)*100:.1f}%")
            
            return df
            
        except Exception as e:
            logger.error(f"Erro no processamento: {e}")
            print(f"❌ Erro: {e}")
            
            # Salva progresso parcial
            if self.resultados:
                try:
                    df_backup = df.copy()
                    df_backup['cartorio'] = self.resultados + [''] * (len(df) - len(self.resultados))
                    arquivo_backup = f"backup_erro_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    df_backup.to_csv(arquivo_backup, index=False)
                    print(f"💾 Backup salvo: {arquivo_backup}")
                except:
                    pass
            
            raise
            
        finally:
            if self.driver:
                print("🔄 Fechando navegador...")
                self.driver.quit()

def main():
    """Função principal"""
    arquivo_csv = input("📂 Digite o nome do arquivo CSV: ").strip()
    
    if not arquivo_csv:
        arquivo_csv = "enderecos.csv"  # Padrão
    
    if not arquivo_csv.endswith('.csv'):
        arquivo_csv += '.csv'
    
    if not os.path.exists(arquivo_csv):
        print(f"❌ Arquivo '{arquivo_csv}' não encontrado!")
        return
    
    # Pergunta se quer usar modo headless
    headless = input("🖥️  Executar em modo invisível? (s/n): ").lower() in ['s', 'sim']
    
    try:
        scraper = CartorioScraperOtimizado(arquivo_csv, headless=headless)
        resultado = scraper.processar_enderecos()
        
        if resultado is not None:
            print("\n✅ Processamento finalizado com sucesso!")
        else:
            print("\n❌ Processamento não foi concluído")
            
    except KeyboardInterrupt:
        print("\n\n⏹️  Processamento interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")

if __name__ == "__main__":
    main()