import SwiftUI

class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
        return true
    }
}

@main
struct TranscritorApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate
    
    var body: some Scene {
        WindowGroup {
            ContentView()
                .frame(minWidth: 800, minHeight: 500)
                // Usando materiais nativos do mac
                .background(VisualEffectView(material: .windowBackground, blendingMode: .behindWindow))
        }
        .windowStyle(HiddenTitleBarWindowStyle()) // Barra de título unificada e limpa
        .commands {
            SidebarCommands() // Adiciona comandos de mostrar/esconder sidebar nativos
        }
    }
}
