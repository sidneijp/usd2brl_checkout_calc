import bs4
import click
from datetime import datetime
import decimal
from decimal import Decimal
from urllib.parse import urlencode
from urllib.request import Request, urlopen


IOF = Decimal('6.38')


def print_money(value, moeda="R$", decimal_places=2):
    return ('{moeda}{value:,.%sf}' % decimal_places).format(value=value, moeda=moeda)


def custom_round(value, decimal_places=2, rounding=decimal.ROUND_DOWN):
    exp = Decimal(10)**-decimal_places
    return value.quantize(exp, rounding=decimal.ROUND_DOWN)


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
        request = Request(self.url, urlencode(self.payload()).encode())
        resp = urlopen(request)
        if resp.status == 200:
            etree = bs4.BeautifulSoup(resp.read(), features='html.parser')
            ptax_line = etree.select('.tabela tbody tr')[-1].select('td')
            self.ptax_compra = Decimal(ptax_line[2].get_text().replace(',', '.'))
            self.ptax_venda = Decimal(ptax_line[3].get_text().replace(',', '.'))
            self.ptax = (self.ptax_venda + self.ptax_compra) / 2


class USD2BRLConverter(object):
    def convert(self, usd_value):
        usd_value = Decimal(usd_value)
        self.ptax_client.fetch()
        self.ptax = self.ptax_client.ptax_venda
        brl_value = usd_value * self._spread * self.ptax * self.iof
        rounded_value = custom_round(brl_value)
        return rounded_value


class NuBankUSD2BRL(USD2BRLConverter):
    """
    Referência NuBank: https://blog.nubank.com.br/nubank-trava-dolar-no-dia-do-gasto/
    """
    def __init__(self, iof=IOF):
        self.ptax_client = PtaxClient()
        self.iof = (1 + iof/100)
        self._spread = (1 + Decimal('4')/100)


class InterUSD2BRL(USD2BRLConverter):
    """
    Referência Banco Inter: https://ajuda.bancointer.com.br/pt-BR/articles/1520202-como-e-composta-a-taxa-cobrada-em-compras-internacionais
    """
    def __init__(self, iof=IOF):
        self.ptax_client = PtaxClient()
        self.iof = (1 + iof/100)
        self._spread = (1 + Decimal('1')/100)


@click.group()
def cli():
    pass


@cli.command()
@click.argument('value', type=click.FLOAT)
def inter(value):
    calc = InterUSD2BRL()
    click.echo(print_money(calc.convert(value)))


@cli.command()
@click.argument('value', type=click.FLOAT)
def nubank(value):
    calc = NuBankUSD2BRL()
    click.echo(print_money(calc.convert(value)))


if __name__ == '__main__':
    cli()
