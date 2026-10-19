using System;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Threading;
using System.Windows;
using System.Windows.Input;

namespace ff4_patcher;

public partial class MainWindow : Window
{
    private string? GameDir;
    private string LprojDir = "";
    private string[] FontPaths = Array.Empty<string>();

    public MainWindow()
    {
        InitializeComponent();
        InitPaths();
        Log("FF4 TAY 中文补丁 v1.0.3\n");
        if (!File.Exists(Path.Combine(GameDir!, "FF4A.exe")))
        {
            Log("未找到 FF4A.exe，请将安装器放到游戏根目录或其直属补丁文件夹内。");
            InstallBtn.IsEnabled = false;
            return;
        }
        Log("点击「安装补丁」开始安装。");
        Log("如需卸载，请在 Steam 验证游戏文件完整性。");
    }

    private void InitPaths()
    {
        GameDir = AppDomain.CurrentDomain.BaseDirectory;
        if (!File.Exists(Path.Combine(GameDir, "FF4A.exe")))
        {
            var parent = Directory.GetParent(Path.TrimEndingDirectorySeparator(GameDir))?.FullName;
            if (parent != null && File.Exists(Path.Combine(parent, "FF4A.exe"))) GameDir = parent;
        }
        LprojDir = Path.Combine(GameDir, "Resources", "en.lproj");
        // Older builds load arial.ttf; Steam build 24945876 loads Arimo.ttf.
        FontPaths = new[] { Path.Combine(GameDir, "arial.ttf"), Path.Combine(GameDir, "Arimo.ttf") };
    }

    private void Log(string msg)
    {
        Dispatcher.Invoke(() =>
        {
            LogText.Text += msg + "\n";
            LogScroller.ScrollToEnd();
        });
    }

    private void Install_Click(object sender, RoutedEventArgs e)
    {
        if (Process.GetProcessesByName("FF4A").Length > 0)
        {
            MessageBox.Show("请先关闭游戏 (FF4A.exe) 再安装。", "提示", MessageBoxButton.OK, MessageBoxImage.Warning);
            return;
        }
        InstallBtn.IsEnabled = false;
        new Thread(InstallThread).Start();
    }

    private void InstallThread()
    {
        try
        {
            Log("\n========== 安装中 ==========");

            var windir = Environment.GetFolderPath(Environment.SpecialFolder.Windows);
            var fontSource = Path.Combine(windir, "Fonts", "simhei.ttf");
            if (!File.Exists(fontSource))
                throw new Exception("未检测到 SimHei 黑体 (simhei.ttf)，请先安装该字体后重试。");

            Log("正在安装中文资源...");
            ExtractEmbeddedZip();
            Log("已安装 121 个文件");

            Log("正在检测系统中文字体...");
            foreach (var fontPath in FontPaths)
            {
                var backupPath = fontPath + ".chinese-patch.bak";
                if (File.Exists(fontPath) && !File.Exists(backupPath))
                    File.Copy(fontPath, backupPath);
                File.Copy(fontSource, fontPath, true);
                Log($"  SimHei → {Path.GetFileName(fontPath)}");
            }

            Log("\n安装完成！启动 FF4A.exe 即可。");
            Dispatcher.Invoke(() =>
            {
                InstallBtn.IsEnabled = true;
                MessageBox.Show("安装完成！");
            });
        }
        catch (Exception ex)
        {
            Log($"[错误] {ex.Message}");
            Dispatcher.Invoke(() => InstallBtn.IsEnabled = true);
        }
    }

    private void ExtractEmbeddedZip()
    {
        var asm = Assembly.GetExecutingAssembly();
        using var stream = asm.GetManifestResourceStream("ff4_patcher.patch_data.zip");
        if (stream == null) throw new Exception("内置数据包丢失");
        using var zip = new ZipArchive(stream);

        foreach (var entry in zip.Entries)
        {
            if (string.IsNullOrEmpty(entry.Name)) continue;
            // menu.txt goes to game root, everything else to en.lproj
            var baseDir = entry.Name == "menu.txt" ? GameDir! : LprojDir;
            var destPath = Path.Combine(baseDir, entry.FullName);
            var destDir = Path.GetDirectoryName(destPath)!;
            if (!Directory.Exists(destDir)) Directory.CreateDirectory(destDir);
            entry.ExtractToFile(destPath, true);
        }
    }

    private void Window_MouseDown(object sender, MouseButtonEventArgs e)
    {
        if (e.LeftButton == MouseButtonState.Pressed) DragMove();
    }

    private void Close_Click(object sender, RoutedEventArgs e)
    {
        Application.Current.Shutdown();
    }
}
