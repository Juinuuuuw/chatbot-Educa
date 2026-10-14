# Fontes do relatório ABNT

O relatório usa Times New Roman, corpo 12, entrelinhas de 1,5, texto justificado e recuo inicial de 1,25 cm. As margens são de 3 cm à esquerda e no topo e de 2 cm à direita e na base. Diagramas e quadros são gerados junto com o PDF.

O título é LIA COMO ASSISTENTE VIRTUAL DA EDUCA. A identificação na capa e na folha de rosto corresponde à Unidade Curricular de Extensão da professora Glaucia. A autoria do código permanece na lista de referências.

O painel integra o capítulo 10, antes das considerações finais e das referências. Seu conteúdo fica em `painel_abnt.py` para facilitar a manutenção editorial, sem se apresentar como apêndice no relatório. O documento descreve Kokoro/Dora e o encaminhamento ao atendimento humano, sem fixar endereço ou porta de implantação.

Para gerar o relatório, use Python com ReportLab e as fontes Times New Roman disponíveis no Windows:

```powershell
python docs/fontes/build_documento_abnt.py
```

A opção `--sem-painel` gera uma versão sem esse capítulo e ajusta o sumário e as páginas seguintes. `--somente-painel` gera um recorte do capítulo. `--saida caminho.pdf` permite escolher outro destino. Os PDFs antigos do painel separado registram a versão anterior; o documento principal atualizado é `Chatbot_Educa_ABNT.pdf`.
