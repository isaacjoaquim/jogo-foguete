# 🚀 Rumo ao Espaço (Rocket Odyssey)

Um jogo de foguete desenvolvido em **Python** com física dinâmica, consumo e recarga de combustível, transição contínua de camadas atmosféricas e efeitos sonoros sintetizados em tempo real!

---

## 🎮 Como Jogar e Controles

- **Segurar `[ ESPAÇO ]`**: Aciona os propulsores do foguete (acelera na direção do nariz e consome combustível).
- **Teclas `[ A ] / [ D ]` ou `[ ← ] / [ → ]`**: Manobra o foguete para a esquerda ou direita (±30°).
- **Tecla `[ 1 ]`**: Seleciona o **Modo 1: Acadêmico** (Requisitos estritos da atividade).
- **Tecla `[ 2 ]`**: Seleciona o **Modo 2: Aeroespacial** (Realista & Jogável).
- **Tecla `[ TAB ]`**: Alterna entre os dois modos de jogo.
- **Tecla `[ E ]`**: Abre a **Tela de Explicação Física Detalhada** dentro do jogo.
- **Tecla `[ M ]`**: Silencia ou ativa o áudio sintetizado em tempo real.
- **Tecla `[ R ]`**: Reinicia o voo após game over.
- **Tecla `[ ESC ]`**: Sai do jogo (ou volta para a tela anterior).

---

## 🔬 Modos de Jogo & Análise Física

O simulador possui **2 modos de jogo selecionáveis**, permitindo comparar diretamente a teoria acadêmica com a prática aeroespacial:

### 1. Modo 1: Acadêmico (Requisitos da Atividade)
* **Por que existe:** Criado para cumprir rigorosamente os parâmetros nominais prescritos no enunciado acadêmico ($F = 2{,}0 \times 10^6\text{ N}$, $m = 200\text{t}$, $\Delta t = 1/60\text{s}$).
* **Comportamento Físico:** Como a massa total inicial é $200.000\text{ kg}$ e o peso é $P = 1.960.000\text{ N}$, o empuxo tem apenas $40.000\text{ N}$ de folga sobre a gravidade ($TWR = 1{,}02$). A aceleração inicial é de apenas **$0{,}2\text{ m/s}^2$** e, ao inclinar $\pm 30^\circ$, a força vertical cai para $1.732.000\text{ N} < P$, fazendo o foguete **despencar** em curvas.

### 2. Modo 2: Aeroespacial (Opção 1 — Realista & Jogável)
* **Por que existe:** Demonstra como foguetes reais (Falcon 9, Saturn V) são verdadeiramente dimensionados na engenharia aeroespacial, onde o TWR de lançamento é projetado entre $1{,}2$ e $1{,}5$.
* **Comportamento Físico:** Com empuxo calibrado para $2{,}8 \times 10^6\text{ N}$ ($TWR = 1{,}43$), a aceleração inicial é de **$4{,}20\text{ m/s}^2$** (decolagem potente). A rotação é feita por **gimbal contínuo suave ($55^\circ/\text{s}$)** e, mesmo com $30^\circ$ de inclinação, a sustentação vertical é de $2{,}42 \times 10^6\text{ N} > P$, permitindo manobras firmes sem perder altitude.

---

## 🎯 Objetivo & Mecânicas

1. **Permanecer no Ar & Ganhar Altitude**: Tente alcançar a maior altitude possível antes do combustível se esgotar.
2. **Gerenciamento de Combustível**: O combustível é consumido frame a frame conforme o motor fica acionado.
3. **Perigo de Queda**: Se o foguete colidir com o solo, explodirá gerando Game Over.
4. **Efeitos Visuais e Sonoros**: Chamas dinâmicas, fumaça, onda de choque sônica, variação de centro de massa com tanque esvaziando e síntese de áudio harmônica sem arquivos externos.

---

## 🕹️ Como Executar

Execute o comando no terminal:
```bash
py main.py
```
Ou dê dois cliques no arquivo `jogar.bat`.
