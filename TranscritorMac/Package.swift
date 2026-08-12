// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "TranscritorMac",
    defaultLocalization: "en",
    platforms: [
        .macOS(.v14) // SwiftUI e WhisperKit requerem versões recentes do macOS
    ],
    dependencies: [
        .package(url: "https://github.com/argmaxinc/WhisperKit.git", exact: "0.9.0")
    ],
    targets: [
        .executableTarget(
            name: "TranscritorMac",
            dependencies: [
                .product(name: "WhisperKit", package: "WhisperKit")
            ],
            path: "Sources/TranscritorMac",
            resources: [
                .process("Resources")
            ]
        )
    ]
)
