## Run:
`python main.py <cc-issuer> <value>`

cc-issuer: (nubank | inter) name of the credit card issuer (to calculate fees)
value: decimal value in USD Dollars

The result is a decimal value in Brasilian Reais (BRL/R$).

## Examples:
```
$ python main.py nubank 10.0
43.30
```

```
$ python main.py inter 10.0
42.05
```
