
from random import choice


class MessageDefault:
    
    def __init__(self):
        
        self.messages_content = [
            "Oi, tudo bem?",
            "Tudo sim, e você?",
            "Também tô bem, graças a Deus!",
            "Tá livre hoje à noite?",
            "Bora sair pra comer alguma coisa?",
            "Que horas você pode?",
            "Pode ser às 19h?",
            "Fechado então!",
            "Me avisa quando estiver chegando.",
            "Ok!",
            "Você viu o que aconteceu ontem?",
            "Nossa, nem acredito!",
            "Depois me conta os detalhes.",
            "Claro, te ligo mais tarde.",
            "Tô indo agora, chego em 15 minutos.",
            "Tranquilo, tô aqui esperando.",
            "Esqueci de te mandar o documento.",
            "Sem problemas, pode mandar agora?",
            "Acabei de enviar no e-mail!",
            "Recebido, obrigado!",
            "Hoje o dia tá corrido por aqui.",
            "Nem me fala, muita reunião!",
            "Bora marcar uma folga semana que vem?",
            "Tô dentro!",
            "Qualquer novidade me chama.",
            "Pode deixar!",
            "Boa noite!",
            "Boa noite, dorme bem!",
            "Bom diaaa!",
            "Bom dia! Como foi o dia ontem?"
        ]


    def get_message(self):
        return choice(self.messages_content)

