import SwiftUI
import WhisperKit

@MainActor
class TranscriptionEngine: ObservableObject {
    @Published var selectedTab: AppTab? = .single
    @Published var isTranscribing = false
    @Published var progressText: LocalizedStringKey = ""
    @Published var progressValue: Double = 0.0
    @Published var transcribedText = ""
    
    @Published var filePath = ""
    @Published var outputDir = ""
    
    // Batch
    struct BatchItem: Identifiable, Hashable {
        let id = UUID()
        let filePath: String
        let outputDir: String
        var status: LocalizedStringKey = "Aguardando"
        
        // For UI checks we keep a separate raw status or just rely on the specific keys
        var isCompleted: Bool { status == "Concluído" }
        var isFailed: Bool { status == "Falhou" }
        
        static func == (lhs: BatchItem, rhs: BatchItem) -> Bool {
            lhs.id == rhs.id
        }
        
        func hash(into hasher: inout Hasher) {
            hasher.combine(id)
        }
    }
    @Published var batchItems: [BatchItem] = []
    @Published var batchSelection = Set<BatchItem.ID>()
    
    // Models
    @Published var activeModel: String = "openai_whisper-base"
    @Published var availableModels: [String] = [
        "openai_whisper-base",
        "openai_whisper-small",
        "openai_whisper-medium",
        "openai_whisper-large-v3-v20240930"
    ]
    @Published var downloadedModels: [String] = []
    
    // Languages
    @Published var selectedLanguage: String = "auto"
    let availableLanguages = ["auto", "pt", "en", "es", "fr", "de", "zh"]
    
    private var pipe: WhisperKit?
    private var currentTask: Task<Void, Never>?
    private var currentLoadedModel: String?
    
    func loadModel(modelName: String = "openai_whisper-base") async {
        do {
            progressText = "Carregando modelo \(modelName)"
            pipe = try await WhisperKit(model: modelName)
            currentLoadedModel = modelName
            progressText = "Modelo carregado."
        } catch {
            let err = error.localizedDescription
            progressText = "Erro ao carregar modelo: \(err)"
        }
    }
    
    func startTranscription(filePath: String, outputDir: String) {
        isTranscribing = true
        progressText = "Iniciando transcrição..."
        progressValue = 0.1
        
        currentTask = Task {
            do {
                if pipe == nil || currentLoadedModel != activeModel {
                    await loadModel(modelName: activeModel)
                }
                
                guard let whisperPipe = pipe else {
                    progressText = "Falha ao inicializar o WhisperKit."
                    isTranscribing = false
                    return
                }
                
                let fileName = URL(fileURLWithPath: filePath).lastPathComponent
                progressText = "Transcrevendo \(fileName)"
                
                var options: DecodingOptions? = nil
                if selectedLanguage != "auto" {
                    options = DecodingOptions(language: selectedLanguage)
                }
                
                // Transcreve o áudio
                let result = try await whisperPipe.transcribe(
                    audioPath: filePath,
                    decodeOptions: options,
                    callback: { progress in
                        DispatchQueue.main.async {
                            self.transcribedText = progress.text
                        }
                        return nil
                    }
                ).first
                
                guard let finalResult = result else {
                    progressText = "Falha na transcrição."
                    isTranscribing = false
                    return
                }
                
                progressValue = 0.8
                progressText = "Gerando arquivos de saída..."
                
                // Salvar saídas
                try saveOutputs(result: finalResult, filePath: filePath, outputDir: outputDir)
                
                progressValue = 1.0
                progressText = "Transcrição Concluída!"
                
            } catch {
                progressText = "Erro: \(error.localizedDescription)"
            }
            
            isTranscribing = false
        }
    }
    
    func startBatchTranscription() {
        guard !isTranscribing else { return }
        
        currentTask = Task {
            for (index, item) in batchItems.enumerated() {
                if Task.isCancelled { break }
                
                // Atualiza status do item atual
                DispatchQueue.main.async {
                    self.batchItems[index].status = "Transcrevendo..."
                }
                
                // Transcreve bloqueando (usamos a mesma lógica principal, mas adaptada para o lote)
                isTranscribing = true
                let fileName = URL(fileURLWithPath: item.filePath).lastPathComponent
                progressText = "Lote: Transcrevendo \(fileName)"
                progressValue = 0.1
                
                do {
                    if pipe == nil || currentLoadedModel != activeModel {
                        await loadModel(modelName: activeModel)
                    }
                    guard let whisperPipe = pipe else { throw NSError(domain: "WhisperKit", code: 1, userInfo: [NSLocalizedDescriptionKey: "Falha ao carregar modelo"]) }
                    
                    var options: DecodingOptions? = nil
                    if selectedLanguage != "auto" {
                        options = DecodingOptions(language: selectedLanguage)
                    }
                    
                    let result = try await whisperPipe.transcribe(
                        audioPath: item.filePath,
                        decodeOptions: options,
                        callback: { progress in
                            DispatchQueue.main.async {
                                self.transcribedText = progress.text
                            }
                            return nil
                        }
                    ).first
                    
                    if let finalResult = result {
                        try saveOutputs(result: finalResult, filePath: item.filePath, outputDir: item.outputDir)
                        DispatchQueue.main.async {
                            self.batchItems[index].status = "Concluído"
                        }
                    } else {
                        DispatchQueue.main.async {
                            self.batchItems[index].status = "Falhou"
                        }
                    }
                } catch {
                    DispatchQueue.main.async {
                        self.batchItems[index].status = "Erro"
                    }
                }
                
                isTranscribing = false
            }
            
            progressText = "Lote Concluído!"
            progressValue = 1.0
        }
    }
    
    func addToBatch(filePath: String, outputDir: String) {
        let out = outputDir.isEmpty ? (URL(fileURLWithPath: filePath).deletingLastPathComponent().path) : outputDir
        let item = BatchItem(filePath: filePath, outputDir: out)
        batchItems.append(item)
    }
    
    func removeFromBatch() {
        let offsets = IndexSet(batchItems.enumerated().filter { batchSelection.contains($0.element.id) }.map { $0.offset })
        batchItems.remove(atOffsets: offsets)
        batchSelection.removeAll()
    }
    
    func deleteModel(_ modelName: String) {
        // Models are usually cached in HF caches or app support.
        // WhisperKit provides `WhisperKit.formatModelPath` or similar, but simpler is to rely on user interaction or finding it in the file system.
        // For simplicity, we just remove it from downloadedModels list since standard CoreML models cached via HF are in a hidden `.cache/huggingface` folder.
        if let idx = downloadedModels.firstIndex(of: modelName) {
            downloadedModels.remove(at: idx)
        }
    }
    
    func cancelTranscription() {
        currentTask?.cancel()
        isTranscribing = false
        progressText = "Transcrição Cancelada."
        progressValue = 0.0
    }
    
    private func saveOutputs(result: TranscriptionResult, filePath: String, outputDir: String) throws {
        let fileURL = URL(fileURLWithPath: filePath)
        let slug = fileURL.deletingPathExtension().lastPathComponent
        
        let outDirURL = URL(fileURLWithPath: outputDir)
        try FileManager.default.createDirectory(at: outDirURL, withIntermediateDirectories: true)
        
        // Texto corrido (.txt)
        let txtURL = outDirURL.appendingPathComponent("\(slug).txt")
        try result.text.write(to: txtURL, atomically: true, encoding: .utf8)
        
        // VTT e SRT usam os segmentos
        var srtBlocks = ""
        var vttBlocks = "WEBVTT\n\n"
        var tsBlocks = ""
        
        for (i, segment) in result.segments.enumerated() {
            let start = segment.start
            let end = segment.end
            let text = segment.text.trimmingCharacters(in: .whitespacesAndNewlines)
            
            let srtStart = formatTime(seconds: start, separator: ",")
            let srtEnd = formatTime(seconds: end, separator: ",")
            
            let vttStart = formatTime(seconds: start, separator: ".")
            let vttEnd = formatTime(seconds: end, separator: ".")
            
            srtBlocks += "\(i + 1)\n\(srtStart) --> \(srtEnd)\n\(text)\n\n"
            vttBlocks += "\(vttStart) --> \(vttEnd)\n\(text)\n\n"
            
            let hmsStart = formatHMS(seconds: start)
            tsBlocks += "[\(hmsStart)] \(text)\n"
        }
        
        let srtURL = outDirURL.appendingPathComponent("\(slug).srt")
        try srtBlocks.write(to: srtURL, atomically: true, encoding: .utf8)
        
        let vttURL = outDirURL.appendingPathComponent("\(slug).vtt")
        try vttBlocks.write(to: vttURL, atomically: true, encoding: .utf8)
        
        let tsURL = outDirURL.appendingPathComponent("\(slug).timestamped.txt")
        try tsBlocks.write(to: tsURL, atomically: true, encoding: .utf8)
    }
    
    private func formatTime(seconds: Float, separator: String) -> String {
        let totalMs = Int(round(seconds * 1000))
        let ms = totalMs % 1000
        let totalS = totalMs / 1000
        let s = totalS % 60
        let totalM = totalS / 60
        let m = totalM % 60
        let h = totalM / 60
        return String(format: "%02d:%02d:%02d%@%03d", h, m, s, separator, ms)
    }
    
    private func formatHMS(seconds: Float) -> String {
        let totalS = Int(seconds)
        let s = totalS % 60
        let totalM = totalS / 60
        let m = totalM % 60
        let h = totalM / 60
        return String(format: "%02d:%02d:%02d", h, m, s)
    }
}
