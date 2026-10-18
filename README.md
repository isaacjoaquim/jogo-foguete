# 🚀 Rumo ao Espaço (Rocket Odyssey)

Um jogo de foguete desenvolvido em **Python** com física dinâmica, consumo e recarga de combustível, transição contínua de camadas atmosféricas e efeitos sonoros sintetizados em tempo real!

---

## 🎮 Como Jogar e Controles

- **Setas `[ ← ] / [ → ]` (ou `[ A ] / [ D ]`) no Menu**: Alterna a seleção entre o **Modo 1: Acadêmico** e **Modo 2: Aeroespacial**.
- **Setas `[ ↑ ] / [ ↓ ]` (ou `[ W ] / [ S ]`) no Menu**: Navega verticalmente pelas opções (Modos, Explicação Física e Botão de Decolagem).
- **`[ ENTER ]` ou `[ ESPAÇO ]` no Menu**: Ativa a opção em foco ou decola imediatamente no modo selecionado.
- **Segurar `[ ESPAÇO ]` em voo**: Aciona os propulsores do foguete (acelera na direção do nariz e consome combustível).
- **Teclas `[ A ] / [ D ]` ou `[ ← ] / [ → ]` em voo**: Manobra o foguete para a esquerda ou direita (±30°).
- **Tecla `[ 1 ]`**: Seleciona diretamente o **Modo 1: Acadêmico** (Requisitos estritos da atividade).
- **Tecla `[ 2 ]`**: Seleciona diretamente o **Modo 2: Aeroespacial** (Realista & Jogável).
- **Tecla `[ TAB ]`**: Alterna rapidamente entre os dois modos de jogo.
- **Tecla `[ E ]`**: Abre a **Tela de Explicação Física Detalhada** dentro do jogo.
- **Tecla `[ M ]`**: Silencia ou ativa o áudio sintetizado em tempo real.
- **Tecla `[ R ]`**: Reinicia o voo após game over ou vitória.
- **Tecla `[ ESC ]`**: Sai do jogo (ou volta para a tela anterior).

---

## 🔬 Modos de Jogo & Análise Física

O simulador possui **2 modos de jogo selecionáveis**, permitindo comparar diretamente a teoria acadêmica com a prática aeroespacial:

### 1. Modo 1: Acadêmico (Requisitos da Atividade)
* **Por que existe:** Criado para cumprir rigorosamente os parâmetros nominais prescritos no enunciado acadêmico ($F = 2{,}0 \times 10^6\text{ N}$, $m = 200\text{t}$, $\Delta t = 1/60\text{s}$).
* **Comportamento Físico:** Como a massa total inicial é $200.000\text{ kg}$ e o peso é $P = 1.960.000\text{ N}$, o empuxo tem apenas $40.000\text{ N}$ de folga sobre a gravidade ($TWR = 1{,}02$). A aceleração inicial é de apenas **$0{,}2\text{ m/s}^2$** e, ao inclinar $\pm 30^\circ$, a força vertical cai para $1.732.000\text{ N} < P$, fazendo o foguete **despencar** em curvas.

### 2. Modo 2: Aeroespacial (Opção 1 — Realista & Jogável)
* **Por que existe:** Demonstra como foguetes reais (Falcon 9, Saturn V) são verdadeiramente dimensionados na engenharia aeroespacial, onde o TWR de lançamento é projetado entre $1{,}2$ e $1{,}8$.
* **Comportamento Físico:** Com empuxo calibrado para $3{,}5 \times 10^6\text{ N}$ ($TWR \approx 1{,}79$), a aceleração inicial é de **$7{,}70\text{ m/s}^2$** (atingindo até **$25{,}2\text{ m/s}^2$** conforme o combustível é consumido), permitindo superar a barreira do som e alcançar o espaço. A rotação é feita por **gimbal contínuo suave ($55^\circ/\text{s}$)** e sustentação positiva firme.

---

## 🎯 Objetivo & Mecânicas Aeroespaciais

1. **Meta de Vitória (Chegada ao Espaço — 10.000 m / 10 km)**: 
   - Pilote o foguete até a altitude alvo de **$10.000\text{ m}$ ($10\text{ km}$)** para vencer a missão e entrar em órbita espacial! Uma tela de vitória completa com fanfarra triunfante e estatísticas de voo será exibida.
   - O HUD exibe a meta, progresso da subida, velocidade em $\text{m/s}$ e número **Mach**.
2. **Efeitos Físicos Realistas Implementados**:
   - 💥 **Barreira do Som e Cone de Prandtl-Glauert (Mach 1.0 = 340 m/s)**: Ao atingir regime transônico/supersônico, o foguete gera um cone de condensação de vapor d'água ao redor da fuselagem, estrondo sônico duplo sintetizado (*Sonic Boom*) e linhas oblíquas de choque de Mach com diamantes de choque (*shock diamonds*) no bocal.
   - 🌌 **Expansão da Pluma do Motor no Vácuo (*Under-expanded Plume*)**: Em baixa altitude a pressão atmosférica comprime o jato de fogo em uma coluna estreita avermelhada; conforme sobe em direção ao espaço, a pluma se expande em um amplo leque de plasma azul, ciano e violeta.
   - 🔇 **Atenuação Acústica no Vácuo Espacial**: Acima de $2.000\text{ m}$, conforme o ar se rarefaz, o som externo do motor e da atmosfera atenua progressivamente até sobrar apenas uma vibração grave e abafada conduzida pela estrutura metálica da fuselagem.
3. **Gerenciamento e Coleta de Combustível Progressivo no Meio do Caminho**:
   - O combustível é consumido frame a frame conforme o motor fica acionado.
   - **Espaçamento Progressivo das Cápsulas (⛽)**: A distância entre as cápsulas aumenta gradativamente ao longo da subida. No início (baixa altitude), os pontos de recarga ficam mais próximos para apoiar o foguete enquanto ainda está pesado e ganhando momento; conforme ganha altitude e velocidade, o espaçamento fica progressivamente maior, exigindo boa conservação de energia e mira.
   - Cada cápsula recarrega **$+20.000\text{ kg}$ ($+20\%$)** do tanque.
   - **Radar de Proximidade nas Bordas**: Setas e marcadores visuais luminosos apontam a direção e distância para as próximas cápsulas.
4. **Vento Lateral Aleatório e Dinâmica Atmosférica**:
   - Correntes de vento suaves e rajadas aleatórias afetam o deslocamento horizontal do foguete na baixa e média atmosfera, diminuindo progressivamente na borda do espaço.
5. **Perigo de Queda**: Se o foguete colidir com o solo, explodirá gerando Game Over.

---

## 🕹️ Como Executar

### Opção 1: Executável Direto (`.exe`) — Não precisa de Python!
Dê dois cliques diretamente no arquivo executável gerado:
```bash
JogoFoguete.exe
```
*(Também disponível na pasta `dist/JogoFoguete.exe`). Arquivo único standalone, pronto para rodar em qualquer Windows 64-bit.*

### Opção 2: Via Python / Script Bat
Execute no terminal:
```bash
py main.py
```
Ou dê dois cliques no arquivo `jogar.bat`.
