# Origem e alterações locais

Código do modelo PT-BR da demonstração oficial ResembleAI/Chatterbox-Multilingual-TTS-pt-br, revisão registrada em SOURCES.json. A licença MIT do Chatterbox está preservada em LICENSE; os avisos Apache existentes nos módulos derivados do CosyVoice foram mantidos.

Na integração Lia, o carregador T3 usa inicialização no dispositivo meta, load_state_dict com assign=True e pesos float16 na GPU. O decoder usa mmap e assign=True. Isso reduz a duplicação temporária de pesos em RAM e o uso de memória de vídeo. A arquitetura, os pesos e a marca d'água são preservados.

Os pesos e a referência original da demonstração são obtidos pelo instalador e não são incluídos no Git. A integração usa, quando presente, a referência sintética própria em assets/lia-reference.wav. O texto é sintetizado localmente após os downloads iniciais.
