using System;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;
using System.Threading;

namespace Lufia2AutoTracker.Helper.Core
{
    public class TrackerClient
    {
        private const string Host = "127.0.0.1";
        private const int Port = 65432;
        private TcpClient _client;
        private NetworkStream _stream;

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

        public event Action<string> CommandReceived;

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
                        int bytesRead = _stream.Read(buffer, 0, buffer.Length);
                        if (bytesRead > 0)
                        {
                            string cmd = Encoding.UTF8.GetString(buffer, 0, bytesRead).Trim();
                            CommandReceived?.Invoke(cmd);
                        }
                    }
                    catch { /* Connection reset handled by sender */ }
                }
                Thread.Sleep(500);
            }
        }

        public void SendState(GameState state)
        {
            if (!IsConnected)
            {
                Connect();
                if (!IsConnected) return; // Retry next time
            }

            try
            {
                string json = JsonSerializer.Serialize(state) + "\n"; // Append newline for delimiting
                byte[] data = Encoding.UTF8.GetBytes(json);
                _stream.Write(data, 0, data.Length);
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
