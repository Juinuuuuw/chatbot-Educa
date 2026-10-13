# Fontes do documento ABNT

O documento principal usa Times New Roman, corpo 12, entrelinhas de 1,5, texto justificado e recuo inicial de 1,25 cm. As margens são de 3 cm à esquerda e no topo e de 2 cm à direita e na base. Diagramas e quadros são produzidos junto com o PDF.

O arquivo `build_documento_abnt.py` conserva os capítulos da versão individual originalmente documentada. O conteúdo opcional do painel está inteiramente em `painel_abnt.py`, acrescentado como Apêndice A após as referências. O painel ocupa as páginas 16 a 20, sem alterar a numeração dos capítulos anteriores.

Para gerar os PDFs, use Python com ReportLab instalado e as fontes Times New Roman disponíveis em `C:/Windows/Fonts`:

```powershell
python docs/fontes/build_documento_abnt.py
python docs/fontes/build_documento_abnt.py --somente-painel
```

Para retirar o painel do documento, execute:

```powershell
python docs/fontes/build_documento_abnt.py --sem-painel
```

Essa opção retira o apêndice e sua entrada no sumário, mantendo o restante do conteúdo. Não é necessário apagar o código da seção nem reorganizar os capítulos. Os resultados são gravados em `outputs`. A opção `--saida caminho.pdf` permite escolher outro destino sem substituir o arquivo padrão.
