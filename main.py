import bs4
import click
from datetime import date, datetime, timedelta
import decimal
from decimal import Decimal
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import csv


IOF = Decimal('5.38')


class BusinessDaysRepository(object):
    def __init__(self):
        self.holidays = {}

    def load(self):
        with open("feriados_nacionais.csv") as f:
            reader = csv.reader(f)
            header = next(reader)
            for row in reader:
                holiday_date_string = row[0]
                holiday_name = row[2]
                holiday_date = datetime.strptime(holiday_date_string, "%m/%d/%Y")
                self.holidays[holiday_date] = self.holidays.get(holiday_date, []) + [holiday_name]

    def get_previous_business_day(self, date, include_itself=False):
        if not include_itself:
            date = date - timedelta(days=1)
        while (not self.is_business_day(date)):
            date = date - timedelta(days=1)
        return date

    def is_business_day(self, date):
        return self.is_weekday(date) and not self.is_holiday(date)

    def is_weekday(self, date):
        return date.weekday() < 5

    def is_holiday(self, date):
        return date in self.holidays


BusinessDays = BusinessDaysRepository()
BusinessDays.load()

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
        start_date = date or datetime.today()
        start_date = self.get_latest_available_date(start_date)
        start_date = start_date.strftime('%d/%m/%Y')
        return {
            'DATAINI': start_date,
            'DATAFIM': "",
            'ChkMoeda': self.dollar_eua_id,
            'RadOpcao': self.boletim_data_especifica
        }

    def get_latest_available_date(self, date):
        return BusinessDays.get_previous_business_day(date, include_itself=True)

    def fetch(self):
        request = Request(self.url, urlencode(self.payload()).encode())
        resp = urlopen(request)
        if resp.status == 200:
            content = resp.read()
            etree = bs4.BeautifulSoup(content, features='html.parser')
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
