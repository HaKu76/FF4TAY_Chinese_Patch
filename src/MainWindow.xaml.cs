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
    private string ArialPath = "";

    public MainWindow()
    {
        InitializeComponent();
        InitPaths();
        Log("FF4 TAY 中文补丁 v1.0\n");
        Log("点击「安装补丁」开始安装。");
        Log("如需卸载，请在 Steam 验证游戏文件完整性。");
    }

    private void InitPaths()
    {
        GameDir = AppDomain.CurrentDomain.BaseDirectory;
        LprojDir = Path.Combine(GameDir, "Resources", "en.lproj");
        ArialPath = Path.Combine(GameDir, "arial.ttf");
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

            Log("正在安装中文资源...");
            ExtractEmbeddedZip();
            Log("已安装 121 个文件");

            Log("正在检测系统中文字体...");
            var windir = Environment.GetFolderPath(Environment.SpecialFolder.Windows);
            var fonts = new (string Name, string Path)[]
            {
                ("SimHei",          System.IO.Path.Combine(windir, "Fonts", "simhei.ttf")),
                ("Microsoft YaHei", System.IO.Path.Combine(windir, "Fonts", "msyh.ttc")),
                ("DengXian",        System.IO.Path.Combine(windir, "Fonts", "Deng.ttf")),
                ("SimSun",          System.IO.Path.Combine(windir, "Fonts", "simsun.ttc")),
            };
            bool found = false;
            foreach (var (name, fp) in fonts)
            {
                if (File.Exists(fp))
                {
                    File.Copy(fp, ArialPath, true);
                    Log($"  字体: {name}");
                    found = true;
                    break;
                }
            }
            if (!found) Log("  (未检测到系统中文字体)");

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
