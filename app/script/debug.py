import datetime
import pytz

class DebugPrinter:
    COLORS = {
        'none': '\033[0m',       # No color
        'debug': '\033[92m',    # Bright Green
        'warning': '\033[93m',  # Bright Yellow
        'error': '\033[91m',    # Bright Red
        'end': '\033[0m'        # Reset
    }

    @staticmethod
    def print(message, level="none", prefix=True, output_path=None):
        level = level.lower()
        color = DebugPrinter.COLORS.get(level, DebugPrinter.COLORS['none'])
        prefix = {
            'debug': '[DEBUG]',
            'warning': '[WARNING]',
            'error': '[ERROR]'
        }.get(level)
        
        if output_path:
            with open(output_path, 'a', encoding='utf-8') as f:
                if prefix is True:
                    f.write(f"{prefix} {message}\n")
                else:
                    f.write(f"{message}\n")
            return

        if prefix is True:
            print(f"{color}{prefix} {message}{DebugPrinter.COLORS['end']}", flush=True)
        else:
            print(f"{color}{message}{DebugPrinter.COLORS['end']}", flush=True)
    
    @staticmethod
    def print_ts(message, level="none", prefix=True, output_path=None):
        level = level.lower()
        color = DebugPrinter.COLORS.get(level, DebugPrinter.COLORS['none'])
        now = datetime.datetime.now(pytz.utc)
        jst = pytz.timezone('Asia/Tokyo')
        now_jst = now.astimezone(jst)
        prefix = f"[{now_jst.strftime('%Y-%m-%d %H:%M:%S')}]"
        
        if output_path:
            with open(output_path, 'a', encoding='utf-8') as f:
                if prefix is True:
                    f.write(f"{prefix} {message}\n")
                else:
                    f.write(f"{message}\n")
            return

        if prefix is True:
            print(f"{color}{prefix} {message}{DebugPrinter.COLORS['end']}", flush=True)
        else:
            print(f"{color}{message}{DebugPrinter.COLORS['end']}", flush=True)
        
    
            
debug_printer = DebugPrinter()  # Create a singleton instance for easy access
            