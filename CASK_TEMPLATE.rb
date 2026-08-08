cask "transcritor-local" do
  version "1.0.0"
  # O SHA256 do arquivo ZIP. Após gerar o zip, rode `shasum -a 256 TranscritorLocal.zip` no terminal para descobrir.
  sha256 "INSERIR_SHA256_AQUI"

  # A URL de onde o brew vai baixar o ZIP gerado pelo PyInstaller (Geralmente nas Releases do GitHub)
  url "https://github.com/SEU_USUARIO/transcritor-local/releases/download/v#{version}/TranscritorLocal.zip"
  
  name "Transcritor Local"
  desc "Transcreve áudios e vídeos localmente usando faster-whisper"
  homepage "https://github.com/marcosaccioly/transcritor-local"

  app "TranscritorLocal.app"

  zap trash: [
    "~/Library/Application Support/TranscritorLocal",
    "~/Library/Preferences/com.transcritorlocal.plist",
  ]
end
