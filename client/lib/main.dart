import 'package:flutter/material.dart';
import 'package:media_kit/media_kit.dart';
import 'pages/home_page.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  MediaKit.ensureInitialized();
  runApp(const PornGeminiApp());
}

class PornGeminiApp extends StatelessWidget {
  const PornGeminiApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'PornGemini',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        primarySwatch: Colors.red,
        scaffoldBackgroundColor: Colors.black87,
        cardColor: Colors.black45,
        appBarTheme: const AppBarTheme(
          backgroundColor: Colors.black,
          elevation: 2,
        ),
        useMaterial3: true,
      ),
      home: const HomePage(),
    );
  }
}
