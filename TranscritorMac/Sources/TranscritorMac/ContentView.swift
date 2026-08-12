import SwiftUI
import AppKit

enum AppTab: String, Hashable, Identifiable {
    case single, batch, models, about
    var id: AppTab { self }
}

struct ContentView: View {
    @StateObject private var engine = TranscriptionEngine()
    
    let allTabs: [AppTab] = [.single, .batch, .models, .about]
    
    var body: some View {
        NavigationSplitView {
            List(allTabs, selection: $engine.selectedTab) { tab in
                if tab == .single {
                    Label("Arquivo Único", systemImage: "doc")
                } else if tab == .batch {
                    Label("Fila (Lote)", systemImage: "list.bullet")
                } else if tab == .models {
                    Label("Modelos", systemImage: "cpu")
                } else if tab == .about {
                    Label("Sobre", systemImage: "info.circle")
                }
            }
            .navigationTitle("Simple Transcribe")
            .listStyle(SidebarListStyle())
        } detail: {
            ZStack {
                // Efeito Vibrancy Native no fundo (Transparência macOS)
                VisualEffectView(material: .hudWindow, blendingMode: .behindWindow)
                    .ignoresSafeArea()
                
                VStack {
                    if engine.selectedTab == .single {
                        SingleFileView(engine: engine)
                    } else if engine.selectedTab == .batch {
                        BatchView(engine: engine)
                    } else if engine.selectedTab == .models {
                        ModelsView(engine: engine)
                    } else if engine.selectedTab == .about {
                        AboutView()
                    }
                }
                .padding()
            }
        }
    }
}

struct SingleFileView: View {
    @ObservedObject var engine: TranscriptionEngine
    
    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            Text("Transcrição Única")
                .font(.largeTitle)
                .fontWeight(.bold)
            
            GroupBox {
                VStack(spacing: 15) {
                    HStack {
                        Button(action: {
                            selectMedia()
                        }) {
                            Text("Selecionar Mídia")
                        }
                        TextField("Caminho do arquivo", text: $engine.filePath)
                            .disabled(true)
                    }
                    
                    HStack {
                        Button(action: {
                            selectOutputDir()
                        }) {
                            Text("Salvar Em")
                        }
                        TextField("Pasta de destino", text: $engine.outputDir)
                            .disabled(true)
                    }
                    HStack {
                        Picker("Idioma do Áudio", selection: $engine.selectedLanguage) {
                            Text("Automático").tag("auto")
                            Text("Português").tag("pt")
                            Text("Inglês").tag("en")
                            Text("Espanhol").tag("es")
                            Text("Francês").tag("fr")
                            Text("Mandarim").tag("zh")
                        }
                        .pickerStyle(.menu)
                    }
                }
                .padding()
            }
            
            HStack {
                Button(action: {
                    if !engine.filePath.isEmpty {
                        let out = engine.outputDir.isEmpty ? (URL(fileURLWithPath: engine.filePath).deletingLastPathComponent().path) : engine.outputDir
                        engine.startTranscription(filePath: engine.filePath, outputDir: out)
                    }
                }) {
                    Text("Iniciar Transcrição")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.large)
                .disabled(engine.isTranscribing || engine.filePath.isEmpty)
                
                Button(action: {
                    if !engine.filePath.isEmpty {
                        engine.addToBatch(filePath: engine.filePath, outputDir: engine.outputDir)
                        engine.filePath = ""
                    }
                }) {
                    Label("Adicionar Lote", systemImage: "plus")
                }
                .buttonStyle(.bordered)
                .controlSize(.large)
                .disabled(engine.filePath.isEmpty)
                
                Button("Parar") {
                    engine.cancelTranscription()
                }
                .buttonStyle(.bordered)
                .controlSize(.large)
                .disabled(!engine.isTranscribing)
            }
            
            if engine.isTranscribing || engine.progressValue > 0 {
                VStack(alignment: .leading) {
                    ProgressView(value: engine.progressValue)
                    Text(engine.progressText)
                        .font(.caption)
                        .foregroundColor(.secondary)
                    
                    if !engine.transcribedText.isEmpty {
                        ScrollView {
                            Text(engine.transcribedText)
                                .font(.body)
                                .foregroundColor(.primary)
                                .padding()
                                .frame(maxWidth: .infinity, alignment: .leading)
                        }
                        .frame(height: 150)
                        .background(Color(NSColor.textBackgroundColor).opacity(0.5))
                        .cornerRadius(8)
                    }
                }
                .padding(.top, 10)
            }
            
            Spacer()
        }
        .padding()
    }
    
    private func selectMedia() {
        let panel = NSOpenPanel()
        panel.allowsMultipleSelection = false
        panel.canChooseDirectories = false
        if panel.runModal() == .OK {
            if let url = panel.url {
                engine.filePath = url.path
            }
        }
    }
    
    private func selectOutputDir() {
        let panel = NSOpenPanel()
        panel.allowsMultipleSelection = false
        panel.canChooseDirectories = true
        panel.canChooseFiles = false
        if panel.runModal() == .OK {
            if let url = panel.url {
                engine.outputDir = url.path
            }
        }
    }
}

struct BatchView: View {
    @ObservedObject var engine: TranscriptionEngine
    
    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            HStack {
                Text("Fila de Transcrição")
                    .font(.largeTitle)
                    .fontWeight(.bold)
                
                Spacer()
                
                Picker("Idioma", selection: $engine.selectedLanguage) {
                    Text("Automático").tag("auto")
                    Text("Português").tag("pt")
                    Text("Inglês").tag("en")
                    Text("Espanhol").tag("es")
                    Text("Francês").tag("fr")
                    Text("Mandarim").tag("zh")
                }
                .pickerStyle(.menu)
                .frame(width: 200)
            }
            
            List(engine.batchItems, selection: $engine.batchSelection) { item in
                HStack {
                    VStack(alignment: .leading) {
                        Text(URL(fileURLWithPath: item.filePath).lastPathComponent)
                            .font(.headline)
                        Text("Saída: \(item.outputDir)")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    Spacer()
                    Text(item.status)
                        .foregroundColor(item.isCompleted ? .green : (item.isFailed ? .red : .primary))
                }
                .tag(item.id)
            }
            .listStyle(.inset)
            .frame(minHeight: 200)
            
            HStack {
                Button(action: {
                    engine.removeFromBatch()
                }) {
                    Label("Remover Selecionados", systemImage: "minus")
                }
                .disabled(engine.batchSelection.isEmpty)
                
                Spacer()
                
                Button("Processar Lote") {
                    engine.startBatchTranscription()
                }
                .buttonStyle(.borderedProminent)
                .disabled(engine.batchItems.isEmpty || engine.isTranscribing)
                
                Button("Parar") {
                    engine.cancelTranscription()
                }
                .disabled(!engine.isTranscribing)
            }
        }
        .padding()
    }
}

struct ModelsView: View {
    @ObservedObject var engine: TranscriptionEngine
    
    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            Text("Gerenciamento de Modelos")
                .font(.largeTitle)
                .fontWeight(.bold)
            
            Picker("Modelo Ativo", selection: $engine.activeModel) {
                ForEach(engine.availableModels, id: \.self) { model in
                    Text(model).tag(model)
                }
            }
            .pickerStyle(.menu)
            
            List {
                ForEach(engine.availableModels, id: \.self) { model in
                    HStack {
                        Text(model)
                            .font(.headline)
                        
                        Spacer()
                        
                        if engine.activeModel == model {
                            Text("Ativo")
                                .foregroundColor(.green)
                                .padding(.trailing, 10)
                        }
                        
                        Button("Baixar") {
                            Task {
                                await engine.loadModel(modelName: model)
                            }
                        }
                        
                        Button("Deletar") {
                            engine.deleteModel(model)
                        }
                        .foregroundColor(.red)
                    }
                    .padding(.vertical, 5)
                }
            }
            .listStyle(.inset)
            
            if engine.isTranscribing || engine.progressValue > 0 {
                VStack(alignment: .leading) {
                    ProgressView(value: engine.progressValue)
                    Text(engine.progressText)
                        .font(.caption)
                }
            }
        }
        .padding()
    }
}

struct AboutView: View {
    var body: some View {
        VStack(spacing: 20) {
            Image(systemName: "waveform.circle.fill")
                .resizable()
                .frame(width: 100, height: 100)
                .foregroundColor(.blue)
            
            Text("Simple Transcribe")
                .font(.largeTitle)
                .fontWeight(.bold)
            
            Text("Versão 1.0")
                .font(.headline)
                .foregroundColor(.secondary)
            
            Text("Desenvolvido por Magikarp13")
                .font(.title3)
                .padding(.top, 10)
            
            Text("Powered by WhisperKit e SwiftUI")
                .font(.footnote)
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

// Ponte para o NSVisualEffectView do AppKit
struct VisualEffectView: NSViewRepresentable {
    var material: NSVisualEffectView.Material
    var blendingMode: NSVisualEffectView.BlendingMode
    
    func makeNSView(context: Context) -> NSVisualEffectView {
        let view = NSVisualEffectView()
        view.material = material
        view.blendingMode = blendingMode
        view.state = .active
        return view
    }
    
    func updateNSView(_ nsView: NSVisualEffectView, context: Context) {
        nsView.material = material
        nsView.blendingMode = blendingMode
    }
}
