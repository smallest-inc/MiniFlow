import Foundation
import Combine

/// WebSocket event bus — mirrors the Python backend's broadcast events.
/// ws://127.0.0.1:8765/ws
final class EventStream: ObservableObject {

    static let shared = EventStream()

    // MARK: - Published state

    @Published var agentStatus: String = "idle"
    @Published var lastActionResult: ActionResultPayload?
    @Published var lastOAuthProvider: String?
    @Published var isConnected = false

    // MARK: - Private

    private var task: URLSessionWebSocketTask?
    private var reconnectWorkItem: DispatchWorkItem?

    // Pending transcription continuations keyed by request ID
    private var transcriptContinuations: [String: CheckedContinuation<String, Error>] = [:]

    private init() {}

    // MARK: - Connection

    func connect() {
        guard task == nil else { return }
        let url = URL(string: "ws://127.0.0.1:8765/ws")!
        task = URLSession.shared.webSocketTask(with: url)
        task?.resume()
        // isConnected is set true only on first successful receive, not here
        receive()
    }

    func disconnect() {
        reconnectWorkItem?.cancel()
        task?.cancel(with: .goingAway, reason: nil)
        task = nil
        DispatchQueue.main.async { self.isConnected = false }
    }

    // MARK: - Receive loop

    private func receive() {
        task?.receive { [weak self] result in
            switch result {
            case .success(let message):
                // Mark connected on first successful message from the backend
                DispatchQueue.main.async { self?.isConnected = true }
                if case .string(let text) = message { self?.dispatch(text) }
                self?.receive()  // keep listening
            case .failure:
                self?.scheduleReconnect()
            }
        }
    }

    private func scheduleReconnect() {
        disconnect()
        let item = DispatchWorkItem { [weak self] in self?.connect() }
        reconnectWorkItem = item
        DispatchQueue.main.asyncAfter(deadline: .now() + 2, execute: item)
    }

    // MARK: - Send audio for transcription

    func transcribe(wavData: Data, bundleID: String?) async throws -> String {
        let reqID = UUID().uuidString
        let payload: [String: Any] = [
            "type": "transcribe",
            "id": reqID,
            "audio": wavData.base64EncodedString(),
            "bundleID": bundleID as Any,
        ]
        let json = try JSONSerialization.data(withJSONObject: payload)
        let text = String(data: json, encoding: .utf8)!

        return try await withCheckedThrowingContinuation { continuation in
            transcriptContinuations[reqID] = continuation
            task?.send(.string(text)) { [weak self] error in
                if let error {
                    self?.transcriptContinuations.removeValue(forKey: reqID)
                    continuation.resume(throwing: error)
                }
            }
        }
    }

    // MARK: - Event dispatch

    private func dispatch(_ text: String) {
        guard
            let data = text.data(using: .utf8),
            let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
            let event = json["event"] as? String
        else { return }

        // Handle transcription response — resume the waiting continuation
        if event == "transcript",
           let reqID = json["id"] as? String,
           let payload = json["payload"] as? [String: Any],
           let transcript = payload["transcript"] as? String {
            let continuation = transcriptContinuations.removeValue(forKey: reqID)
            continuation?.resume(returning: transcript)
            return
        }

        guard let payload = json["payload"] else { return }

        DispatchQueue.main.async {
            switch event {
            case "agent-status":
                self.agentStatus = payload as? String ?? "idle"

            case "action-result":
                guard let p = payload as? [String: Any] else { return }
                self.lastActionResult = ActionResultPayload(
                    action: p["action"] as? String ?? "",
                    success: p["success"] as? Bool ?? false,
                    message: p["message"] as? String ?? ""
                )

            case "oauth-connected":
                guard let p = payload as? [String: Any] else { return }
                self.lastOAuthProvider = p["provider"] as? String

            default:
                break
            }
        }
    }
}

// MARK: - Event types

struct ActionResultPayload {
    let action: String
    let success: Bool
    let message: String
}
