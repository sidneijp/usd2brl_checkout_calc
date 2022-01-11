import bs4
import click
from datetime import datetime
import requests

IOF = 6.38


class PtaxClient(object):
    """
    Referência Ptax: https://www.bcb.gov.br/conteudo/relatorioinflacao/EstudosEspeciais/EE042_A_taxa_de_cambio_de_referencia_Ptax.pdf
    """
 
    url = 'https://ptax.bcb.gov.br/ptax_internet/consultaBoletim.do?method=consultarBoletim'
    dollar_eua_id = 61
    boletim_data_especifica = 3

    def __init__(self):
        self.ptax = None
        self.ptax_compra = None
        self.ptax_venda = None

    def payload(self, date=None):
        start_date = date or datetime.today().strftime('%d/%m/%Y')
        return {
            'DATAINI': start_date,
            'ChkMoeda': self.dollar_eua_id,
            'RadOpcao': self.boletim_data_especifica
        }

    def fetch(self):
        resp = requests.post(self.url, data=self.payload())
        if resp.status_code == 200:
            etree = bs4.BeautifulSoup(resp.text, features='html.parser')
            ptax_line = etree.select('.tabela tbody tr')[-1].select('td')
            self.ptax_compra = float(ptax_line[2].get_text().replace(',', '.'))
            self.ptax_venda = float(ptax_line[3].get_text().replace(',', '.'))
            self.ptax = (self.ptax_venda + self.ptax_compra) / 2


class NuBankUSD2BRL(object):
    """
    Referência NuBank: https://blog.nubank.com.br/nubank-trava-dolar-no-dia-do-gasto/
    """
    def __init__(self, iof=IOF):
        self.ptax_client = PtaxClient()
        self.iof = (1 + iof/100.)
        self._spread = (1 + 4./100.)

    def convert(self, value):
        self.ptax_client.fetch()
        self.ptax = self.ptax_client.ptax_venda
        return round(value * self._spread * self.ptax * self.iof, 2)

    def pretty(self, value):
        return 'R${0:,.2f}'.format(self.convert(value))


class InterUSD2BRL(object):
    """
    Referência Banco Inter: https://ajuda.bancointer.com.br/pt-BR/articles/1520202-como-e-composta-a-taxa-cobrada-em-compras-internacionais
    """
    def __init__(self, iof=IOF):
        self.ptax_client = PtaxClient()
        self.iof = (1 + iof/100.)
        self._spread = (1 + 1./100.)

    def convert(self, value):
        self.ptax_client.fetch()
        self.ptax = self.ptax_client.ptax
        return round(value * self._spread * self.ptax * self.iof, 2)

    def pretty(self, value):
        return 'R${0:,.2f}'.format(self.convert(value))


@click.group()
def cli():
    pass


@cli.command()
@click.argument('value', type=click.FLOAT)
def inter(value):
    calc = InterUSD2BRL()
    click.echo(calc.convert(value))


@cli.command()
@click.argument('value', type=click.FLOAT)
def nubank(value):
    calc = NuBankUSD2BRL()
    click.echo(calc.convert(value))


if __name__ == '__main__':
    cli()
