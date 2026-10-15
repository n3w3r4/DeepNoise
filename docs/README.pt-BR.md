# DeepNoise — Português (Brasil)

[English](../README.md)


**DeepNoise** cancela ruído em tempo real no Windows, no seu microfone e no som de quem fala com você.

- **Seu ruído**: teclado, ventilador, palmas, rua. Supressão neural com DeepFilterNet3, frames de 10 ms a 48 kHz, ~40 ms de atraso.
- **Ruído dos outros** nas chamadas, **cancelamento de eco** e **microfone virtual** para Discord, Zoom, Teams e OBS.
- Ajuste fino, travar volume do microfone, atalho global **Ctrl+Alt+M**, ícone na bandeja com **ações rápidas**,
  iniciar com o Windows e reconexão automática de dispositivos. Interface em português e inglês.

### Instalar

1. Baixe `DeepNoise-<versão>-win64.zip` em [Releases](https://github.com/n3w3r4/Deep-Noise/releases) e descompacte.
2. Opcional, para usar em outros apps: clique com o botão direito em `install-drivers.ps1` → *Executar com o PowerShell*,
   aceite os instaladores da VB-Audio e reinicie o Windows.
3. Abra o `DeepNoise.exe`. Ele fica na bandeja; fechar a janela não encerra o app.

### Usar no Discord / Zoom / Teams

| No DeepNoise | No app de chamada |
|---|---|
| **Sua voz → Enviar para:** `CABLE Input` | **Microfone:** `CABLE Output (VB-Audio Virtual Cable)` |
| **Quem fala com você → Apps tocam em:** `Hi-Fi Cable Output`, **Você ouve em:** seu fone | **Alto-falante:** `Hi-Fi Cable Input (VB-Audio Hi-Fi Cable)` |

### Compilar

Os mesmos comandos de [Build from source](../README.md#build-from-source). O VB-CABLE e o Hi-Fi Cable são donationware da
VB-Audio (www.vb-cable.com) e não vêm no repositório: o `scripts\install-drivers.ps1` baixa do site oficial e confere a assinatura.


## Licença

O código próprio usa MIT OR Apache-2.0, à sua escolha. Veja [NOTICE](../NOTICE) e [licenças de terceiros](../THIRD_PARTY_NOTICES.md).
