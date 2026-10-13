using System.Runtime.InteropServices;
using Microsoft.Win32.SafeHandles;

internal static class Program
{
    private const uint AttachParentProcess = 0xFFFFFFFF;
    private const int StdOutputHandle = -11;

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool FreeConsole();

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool AttachConsole(uint processId);

    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern IntPtr GetStdHandle(int standardHandle);

    [DllImport("kernel32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    private static extern bool ReadConsoleOutputCharacter(
        IntPtr consoleOutput,
        [Out] char[] buffer,
        uint length,
        Coord readCoord,
        out uint charsRead);

    [StructLayout(LayoutKind.Sequential)]
    private readonly struct Coord(short x, short y)
    {
        public readonly short X = x;
        public readonly short Y = y;
    }

    // 附加目标游戏的控制台并输出其当前屏幕缓冲区，供读取 DivaModLoader 的加载日志。
    private static int Main(string[] args)
    {
        if (args.Length != 1 || !uint.TryParse(args[0], out uint processId))
        {
            Console.Error.WriteLine("用法：GameConsoleReader <游戏进程ID>");
            return 2;
        }

        FreeConsole();
        if (!AttachConsole(processId))
        {
            Console.Error.WriteLine($"无法附加游戏控制台，Windows 错误码：{Marshal.GetLastWin32Error()}");
            return 1;
        }

        IntPtr output = GetStdHandle(StdOutputHandle);
        if (output == IntPtr.Zero || output == new IntPtr(-1))
        {
            Console.Error.WriteLine($"无法读取控制台输出句柄，Windows 错误码：{Marshal.GetLastWin32Error()}");
            return 1;
        }

        const int width = 240;
        const int height = 160;
        char[] buffer = new char[width * height];
        if (!ReadConsoleOutputCharacter(output, buffer, (uint)buffer.Length, new Coord(0, 0), out _))
        {
            Console.Error.WriteLine($"无法读取控制台屏幕缓冲区，Windows 错误码：{Marshal.GetLastWin32Error()}");
            return 1;
        }

        for (int row = 0; row < height; row++)
        {
            string line = new string(buffer, row * width, width).TrimEnd();
            if (!string.IsNullOrWhiteSpace(line))
                Console.WriteLine(line);
        }

        return 0;
    }
}
