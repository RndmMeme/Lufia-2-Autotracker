using System;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;
using System.Threading;

namespace Lufia2AutoTracker.Helper.Core
{
    public sealed class TrackerStatusEnvelope
    {
        [System.Text.Json.Serialization.JsonPropertyName("tracker_status")]
        public TrackerStatus Status { get; init; } = new();
    }

    public sealed class TrackerStatus
    {
        public string State { get; init; } = string.Empty;
        public string Message { get; init; } = string.Empty;
        public string? Process { get; init; }
        public string? Profile { get; init; }
    }

    public class TrackerClient
    {
        private const string Host = "127.0.0.1";
        private const int Port = 65432;
        private TcpClient? _client;
        private NetworkStream? _stream;
        private readonly object _sendLock = new object();

        public bool IsConnected => _client != null && _client.Connected;

        public void Connect()
        {
            try
            {
                if (_client == null || !_client.Connected)
                {
                    _client = new TcpClient();
                    _client.Connect(Host, Port);
                    _stream = _client.GetStream();
                    Console.WriteLine($"Connected to Tracker at {Host}:{Port}");
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Connection failed: {ex.Message}");
                _client = null;
            }
        }

        public event Action<string>? CommandReceived;

        public void StartListening()
        {
             Thread t = new Thread(ListenLoop);
             t.IsBackground = true;
             t.Start();
        }

        private void ListenLoop()
        {
            byte[] buffer = new byte[1024];
            while (true)
            {
                if (IsConnected)
                {
                    try
                    {
                        int bytesRead = _stream!.Read(buffer, 0, buffer.Length);
                        if (bytesRead > 0)
                        {
                            string cmd = Encoding.UTF8.GetString(buffer, 0, bytesRead).Trim();
                            CommandReceived?.Invoke(cmd);
                        }
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine(
                            $"[Warning] [TrackerClient] listener stopped " +
                            $"exception={ex.GetType().Name} message={ex.Message}");
                        _client?.Close();
                        _client = null;
                        _stream = null;
                    }
                }
                Thread.Sleep(500);
            }
        }

        public void SendState(GameState state)
        {
            SendJson(SerializeState(state));
        }

        public void SendStatus(string state, string message, string? processName = null, string? profileName = null)
        {
            var payload = new TrackerStatusEnvelope {
                Status = new TrackerStatus {
                    State = state,
                    Message = message,
                    Process = processName,
                    Profile = profileName
                }
            };
            SendJson(SerializeStatus(payload));
        }

        internal static string SerializeState(GameState state) =>
            JsonSerializer.Serialize(state, TrackerJsonContext.Default.GameState);

        internal static string SerializeStatus(TrackerStatusEnvelope status) =>
            JsonSerializer.Serialize(status, TrackerJsonContext.Default.TrackerStatusEnvelope);

        private void SendJson(string json)
        {
            if (!IsConnected)
            {
                Connect();
                if (!IsConnected) return; // Retry next time
            }

            try
            {
                byte[] data = Encoding.UTF8.GetBytes(json + "\n");
                lock (_sendLock)
                {
                    _stream!.Write(data, 0, data.Length);
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error sending data: {ex.Message}");
                _client?.Close();
                _client = null;
            }
        }
    }
}
