#include <globals.h>

inline HMODULE DllModuleHandle = NULL;
inline wchar_t DllFilePathBuffer[512] = { 0 };

// 在加载器调用 Init 后再创建路径字符串，避免在 Windows loader lock 内分配 C++ 字符串。
inline void InitializeDllFilePath() {
	GetModuleFileNameW(DllModuleHandle, DllFilePathBuffer, 512);
}

inline std::wstring u8string_to_wide_string(char* src)
{
	const auto size_needed = MultiByteToWideChar(CP_UTF8, 0, src, (int)strlen(src), NULL, 0);
	if (size_needed <= 0)
	{
		return L"";
	}

	std::wstring result(size_needed, 0);
	MultiByteToWideChar(CP_UTF8, 0, src, (int)strlen(src), &result.at(0), size_needed);
	return result;
}

inline std::string wide_string_to_u8string(wchar_t* src)
{
	const auto size_needed = WideCharToMultiByte(CP_UTF8, 0, src, (int)wcslen(src), NULL, 0, NULL, NULL);
	if (size_needed <= 0)
	{
		return "";
	}
	std::string result(size_needed, 0);
	WideCharToMultiByte(CP_UTF8, 0, src, (int)wcslen(src), &result.at(0), size_needed, NULL, NULL);
	return result;
}

inline std::string to_utf8(std::wstring wstr) {
	return wide_string_to_u8string(&wstr[0]);
}

inline std::wstring to_wstr(std::string utf8) {
	return u8string_to_wide_string(&utf8[0]);
}

inline std::wstring FullPathInDllFolder(std::wstring fileName) {
	const std::wstring dllFilePath(DllFilePathBuffer);
	std::wstring path = dllFilePath.substr(0, dllFilePath.find_last_of(L"/\\")) + L"\\" + fileName;
	return path;
}

inline std::string FileNameFromPath(std::string path) {
	return path.substr(path.find_last_of("/\\") + 1, path.size());
}
