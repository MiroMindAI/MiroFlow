class TextInterceptor:
    def __init__(self, unbreakable_strings):
        """
        初始化截流器
        
        Args:
            unbreakable_strings (list): 不可被分割的字符串列表
        """
        self.unbreakable_strings = unbreakable_strings
        self.buffer = ""

    def is_unbreakable_string(self, text):
        for unbreakable in self.unbreakable_strings:
            if unbreakable in text:
                return True
        return False
    
    def process(self, text, is_last):
        """
        处理输入的文本流
        
        Args:
            text (str): 输入的文本片段
            is_last (bool): 是否是最后一个片段
            
        Returns:
            str or None: 可以安全输出的文本，如果需要继续缓存则返回None
        """
        # 将新文本添加到缓冲区
        self.buffer += text
        
        # 如果是最后一个片段，需要处理包含不可分割字符串的情况
        if is_last:
            result = self.buffer
            self.buffer = ""
            
            # 检查是否包含完整的不可分割字符串
            for unbreakable in self.unbreakable_strings:
                if unbreakable in result:
                    # 找到不可分割字符串的位置
                    unbreakable_pos = result.find(unbreakable)
                    if unbreakable_pos > 0:
                        # 如果不可分割字符串前面有内容，只输出前面的部分
                        return result[:unbreakable_pos]
                    else:
                        # 如果不可分割字符串在开头，不输出任何内容
                        return None
            
            # 如果不包含任何不可分割字符串，直接输出
            return result
        
        # 检查缓冲区是否可能是某个不可分割字符串的前缀
        might_be_prefix = False
        for unbreakable in self.unbreakable_strings:
            if unbreakable.startswith(self.buffer) and len(self.buffer) < len(unbreakable):
                might_be_prefix = True
                break
        
        # 如果可能是前缀，继续缓存
        if might_be_prefix:
            return None
        
        # 检查是否包含完整的不可分割字符串
        for unbreakable in self.unbreakable_strings:
            if unbreakable in self.buffer:
                # 找到不可分割字符串的位置
                unbreakable_pos = self.buffer.find(unbreakable)
                if unbreakable_pos > 0:
                    # 如果不可分割字符串前面有内容，输出前面的部分
                    result = self.buffer[:unbreakable_pos]
                    # 保留不可分割字符串及其后面的内容在缓冲区中
                    self.buffer = self.buffer[unbreakable_pos:]
                    return result
                else:
                    # 如果不可分割字符串在开头，不输出任何内容，保持缓冲区不变
                    return None
        
        # 如果不包含完整的不可分割字符串，找到最后一个安全的输出位置 
        safe_output_end = 0
        
        for i in range(1, len(self.buffer) + 1):
            current_suffix = self.buffer[safe_output_end:i]
            
            # 检查当前后缀是否是某个不可分割字符串的前缀
            is_dangerous_suffix = False
            for unbreakable in self.unbreakable_strings:
                if unbreakable.startswith(current_suffix) and len(current_suffix) < len(unbreakable):
                    is_dangerous_suffix = True
                    break
            
            # 如果不是危险后缀，更新安全输出位置
            if not is_dangerous_suffix:
                safe_output_end = i
        
        # 如果没有安全输出位置，继续缓存
        if safe_output_end == 0:
            return None
        
        # 输出安全部分，保留可能危险的后缀
        result = self.buffer[:safe_output_end]
        self.buffer = self.buffer[safe_output_end:]
        
        return result if result else None


# 使用示例
if __name__ == "__main__":
    # # 创建截流器，设置不可分割的字符串
    # interceptor = TextInterceptor(["hello", "world", "python"])
    
    # # 模拟流式文本输入
    # stream_inputs = [
    #     ("h", False),
    #     ("e", False),
    #     ("l", False),
    #     ("l", False),
    #     ("o", False),
    #     (" w", False),
    #     ("o", False),
    #     ("r", False),
    #     ("l", False),
    #     ("d", False),
    #     (" test", False),
    #     (" py", False),
    #     ("th", False),
    #     ("on", False),
    #     (" end", True)
    # ]
    
    # print("流式处理示例：")
    # for text, is_last in stream_inputs:
    #     result = interceptor.process(text, is_last)
    #     if result is not None:
    #         print(f"输出: '{result}'")
    #     else:
    #         print("缓存中...")
    
    # print("\n" + "="*50)
    
    # # 另一个示例：避免分割"python"
    # interceptor2 = TextInterceptor(["python", "code"])
    
    # inputs2 = [
    #     ("this is py", False),
    #     ("th", False),
    #     ("on co", False),
    #     ("de example", True)
    # ]
    
    # print("第二个示例：")
    # for text, is_last in inputs2:
    #     result = interceptor2.process(text, is_last)
    #     if result is not None:
    #         print(f"输出: '{result}'")
    #     else:
    #         print("缓存中...")



    pass  # 测试代码已移除