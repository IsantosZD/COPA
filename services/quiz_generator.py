import pandas as pd
import json
import os
from typing import List, Dict, Optional
import requests
from datetime import datetime

# Tente importar bibliotecas de IA disponíveis
# Isso é para a evolução do sistema futuramente
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

class QuizGenerator:
    
    def __init__(self, database_url: str, ai_provider: str, api_key: Optional[str] = None, database_type: str = "csv"):
 
        self.database_url = database_url
        self.ai_provider = ai_provider.lower()
        self.database_type = database_type.lower()
        self.api_key = api_key
        self.data = None
        self.client = None
        
        self._initialize_ai_client()
        self._load_database()
    
    def _initialize_ai_client(self):
        if self.ai_provider == "openai" and HAS_OPENAI:
            api_key = self.api_key or os.getenv("OPENAI_API_KEY")
            if api_key:
                self.client = OpenAI(api_key=api_key)
        
        elif self.ai_provider == "anthropic" and HAS_ANTHROPIC:
            api_key = self.api_key or os.getenv("ANTHROPIC_API_KEY")
            if api_key:
                self.client = anthropic.Anthropic(api_key=api_key)
        
        elif self.ai_provider == "mock":
            self.client = None  
    
    def _load_database(self):
        try:
            if self.database_type == "csv":
                if self.database_url.startswith("http"):
                    self.data = pd.read_csv(self.database_url)
                else:
                    self.data = pd.read_csv(self.database_url)
            
            elif self.database_type == "json":
                if self.database_url.startswith("http"):
                    response = requests.get(self.database_url)
                    self.data = pd.DataFrame(response.json())
                else:
                    with open(self.database_url, 'r', encoding='utf-8') as f:
                        self.data = pd.DataFrame(json.load(f))
            
            elif self.database_type == "url":
                response = requests.get(self.database_url)
                if self.database_url.endswith('.csv'):
                    from io import StringIO
                    self.data = pd.read_csv(StringIO(response.text))
                else:
                    self.data = pd.DataFrame(response.json())
            
            print(f"Banco de dados carregado: {self.database_url}")
            print(f"Dimensões: {self.data.shape}")
            
        except Exception as e:
            print(f"Erro ao carregar banco de dados: {e}")
            self.data = None
    
    def _generate_with_openai(self, prompt: str, num_questions: int = 5) -> List[Dict]:
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {
                        "role": "system",
                        "content": "Você é um especialista em futebol, estatística esportiva e história da Copa do Mundo FIFA. Gere perguntas de múltipla escolha baseadas exclusivamente em dados reais, verificáveis e historicamente corretos sobre a Copa do Mundo FIFA."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            content = response.choices[0].message.content
            return self._parse_ai_response(content)
        
        except Exception as e:
            print(f"Erro ao usar OpenAI: {e}")
            return []
    
    def _generate_with_anthropic(self, prompt: str, num_questions: int = 5) -> List[Dict]:
        try:
            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=2000,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            content = response.content[0].text
            return self._parse_ai_response(content)
        
        except Exception as e:
            print(f"Erro ao usar Anthropic: {e}")
            return []
    
    # def _generate_mock_questions(self, num_questions: int = 5) -> List[Dict]:
    #     if self.data is None or self.data.empty:
    #         return self._get_padrao_quiz()
        
    #     questions = []
    #     sample_data = self.data.sample(min(num_questions, len(self.data)))
        
    #     for idx, row in sample_data.iterrows():
    #         col_names = list(self.data.columns)
    #         if len(col_names) >= 2:
    #             col1, col2 = col_names[0], col_names[1]
                
    #             questions.append({
    #                 'q': f'Qual é o valor de "{col1}" para "{row[col1]}"?',
    #                 'a': str(row[col2]),
    #                 'opts': [
    #                     str(row[col2]),
    #                     str(self.data[col2].sample(1).values[0]),
    #                     str(self.data[col2].sample(1).values[0]),
    #                     str(self.data[col2].sample(1).values[0])
    #                 ]
    #             })
    #             questions[-1]['opts'] = list(set(questions[-1]['opts']))[:4]
        
    #     return self._get_padrao_quiz() # Aqui é pra retornar 'questions', mas vou manter as perguntas padrão
    
    def _parse_ai_response(self, content: str) -> List[Dict]:
        try:
            if '```' in content:
                content = '\n'.join(content.split('\n')[1:-1])
            
            # Converte para JSON direto
            data = json.loads(content.strip())
            questions = []
            
            # Valida e extrai perguntas
            for item in (data if isinstance(data, list) else [data]):
                if isinstance(item, dict) and all(k in item for k in ['q', 'a', 'opts']):
                    questions.append(item)
            
            return questions if questions else self._get_padrao_quiz()
        
        except (json.JSONDecodeError, KeyError, ValueError):
            return self._get_padrao_quiz()
    
    
    # Retorna perguntas padrão se houver falha na geração
    def _get_padrao_quiz(self) -> List[Dict]:
        return [
        {'q': 'Qual país sediou a Copa do Mundo de 2022?', 'a': 'Qatar', 'opts': ['Russia', 'Qatar', 'Brasil', 'Alemanha']},
        {'q': 'Quem ganhou a Copa do Mundo de 2022?', 'a': 'Argentina', 'opts': ['França', 'Argentina', 'Marrocos', 'Croácia']},
        {'q': 'Quem foi artilheiro da Copa de 2022?', 'a': 'Mbappé', 'opts': ['Messi', 'Neymar', 'Mbappé', 'Lewandowski']},
        {'q': 'Quantos gols Mbappé marcou na final de 2022?', 'a': '3', 'opts': ['1', '2', '3', '4']},
        {'q': 'Qual seleção surpreendeu chegando às semifinais em 2022?', 'a': 'Marrocos', 'opts': ['Austrália', 'Senegal', 'Marrocos', 'Japão']},
        {'q': 'Quem ganhou a Copa do Mundo de 2018?', 'a': 'França', 'opts': ['Croácia', 'França', 'Bélgica', 'Uruguai']},
        {'q': 'Onde foi realizada a Copa do Mundo de 2018?', 'a': 'Rússia', 'opts': ['Alemanha', 'Rússia', 'Qatar', 'EUA']},
        {'q': 'Quantas vezes o Brasil ganhou a Copa do Mundo?', 'a': '5', 'opts': ['4', '5', '6', '3']},
        {'q': 'Em que ano o Brasil foi goleado 7x1 pela Alemanha?', 'a': '2014', 'opts': ['2010', '2012', '2014', '2016']},
        {'q': 'Qual país tem mais títulos mundiais?', 'a': 'Brasil', 'opts': ['Alemanha', 'Brasil', 'Itália', 'Argentina']}
        ]
    
    def generate_questions(self, num_questions: int = 5, context: str = "") -> List[Dict]:
        if self.data is None or self.data.empty:
            print("Banco de dados vazio, retornando perguntas padrão")
            return self._get_padrao_quiz()
        
        data_sample = self.data.head(10).to_string()
        
        prompt = f"""
        Gere {num_questions} perguntas de múltipla escolha sobre futebol/Copa do Mundo.
        Baseie-se nesses dados:

        {data_sample}

        Contexto adicional: {context if context else 'Geral sobre Copa do Mundo'}

        Formato JSON esperado (responda APENAS com JSON válido):
        [
        {{
            "q": "Pergunta aqui?",
            "a": "Resposta correta",
            "opts": ["Opção 1", "Opção 2", "Opção 3", "Resposta correta"]
        }}
        ]

        Garantias:
        - A resposta correta DEVE estar em opts
        - Todas as opções devem ser diferentes
        - Máximo 4 opções por pergunta(A,B,C, D)

        Regras: 
        - Utilize apenas informações presentes no dataset; 
        - Não invente dados, estatísticas, resultados, jogadores, seleções ou eventos que não estejam registrados no database; 
        - Caso alguma informação necessária não esteja disponível, descarte a pergunta; 
        """
        
        if self.ai_provider == "openai" and self.client:
            return self._generate_with_openai(prompt, num_questions)
        
        elif self.ai_provider == "anthropic" and self.client:
            return self._generate_with_anthropic(prompt, num_questions)
                
        else:
            # print(f"Provedor '{self.ai_provider}' não disponível ou sem chave API")
            # return self._generate_mock_questions(num_questions)
            print("Usando perguntas padrão")
            return self._get_padrao_quiz()
    
    # Resumo dos dados
    def get_data_summary(self) -> Dict:
        if self.data is None:
            return {"status": "error", "message": "Nenhum dado carregado"}
        
        return {
            "status": "Sucesso",
            "rows": len(self.data),
            "columns": len(self.data.columns),
            "column_names": list(self.data.columns),
            "data_types": dict(self.data.dtypes.astype(str)),
            "sample": self.data.head(3).to_dict(orient='records')
        }

# Criar quiz com CSV e JSON 
def create_quiz_from_csv(csv_path: str, num_questions: int = 5) -> List[Dict]:
    generator = QuizGenerator(
        database_url=csv_path,
        ai_provider="mock",
        database_type="csv"
    )
    
    return generator.generate_questions(num_questions)

def create_quiz_from_json(json_path: str, num_questions: int = 5) -> List[Dict]:
    generator = QuizGenerator(
        database_url=json_path,
        ai_provider="mock",
        database_type="json"
    )
    
    return generator.generate_questions(num_questions)