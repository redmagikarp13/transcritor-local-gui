cask "simple-transcribe" do
  version "1.0.0"
  sha256 "f49f452e421c22cc6bb49267b2a2c2c779b855a3504c8bb249011df22a95a672"

  url "https://github.com/redmagikarp13/transcritor-local/releases/download/v#{version}/SimpleTranscribe.zip"
  
  name "Simple Transcribe"
  desc "Transcreve áudios e vídeos localmente usando WhisperKit"
  homepage "https://github.com/redmagikarp13/transcritor-local"

  app "Simple Transcribe.app"

  zap trash: [
    "~/Library/Application Support/Simple Transcribe",
    "~/Library/Preferences/com.magikarp13.SimpleTranscribe.plist",
  ]
end
