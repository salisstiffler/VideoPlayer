import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:video_player/video_player.dart';
import 'package:chewie/chewie.dart';
import 'package:media_kit/media_kit.dart';
import 'package:media_kit_video/media_kit_video.dart' as mk;
import 'dart:io' show Platform;
import 'package:flutter/foundation.dart' show kIsWeb;
import '../models/video.dart';
import '../services/api_service.dart';

class PlayerPage extends StatefulWidget {
  final Video video;
  const PlayerPage({super.key, required this.video});

  @override
  State<PlayerPage> createState() => _PlayerPageState();
}

class _PlayerPageState extends State<PlayerPage> {
  // Mobile/Web Controllers
  VideoPlayerController? _videoPlayerController;
  ChewieController? _chewieController;

  // Windows/Desktop Controllers
  Player? _player;
  mk.VideoController? _mkController;

  VideoDetail? _videoDetail;
  AppVideoFormat? _currentFormat;
  bool _isLoading = true;
  bool _isWindows = !kIsWeb && Platform.isWindows;

  @override
  void initState() {
    super.initState();
    SystemChrome.setEnabledSystemUIMode(SystemUiMode.immersiveSticky);
    if (_isWindows) {
      _player = Player();
      _mkController = mk.VideoController(_player!);
    }
    _loadVideoDetail();
  }

  @override
  void dispose() {
    SystemChrome.setEnabledSystemUIMode(SystemUiMode.manual, overlays: SystemUiOverlay.values);
    _videoPlayerController?.dispose();
    _chewieController?.dispose();
    _player?.dispose();
    super.dispose();
  }

  Future<void> _loadVideoDetail() async {
    try {
      final detail = await ApiService.getVideoDetail(widget.video.url);
      if (detail.formats.isNotEmpty) {
        setState(() {
          _videoDetail = detail;
          _currentFormat = detail.formats.first;
        });
        await _initializePlayer(_currentFormat!.url, _currentFormat!.headers);
      } else {
        throw Exception("No playable formats found");
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error loading video source: $e')),
        );
        setState(() => _isLoading = false);
      }
    }
  }

  Future<void> _initializePlayer(String url, Map<String, String>? headers) async {
    setState(() => _isLoading = true);

    if (_isWindows) {
      await _player!.open(Media(url, httpHeaders: headers));
    } else {
      // Clean up previous controller
      final oldController = _videoPlayerController;
      if (oldController != null) {
        await oldController.pause();
        await oldController.dispose();
      }

      _videoPlayerController = VideoPlayerController.networkUrl(
        Uri.parse(url),
        httpHeaders: headers ?? {},
      );
      await _videoPlayerController!.initialize();

      _chewieController = ChewieController(
        videoPlayerController: _videoPlayerController!,
        autoPlay: true,
        looping: false,
        aspectRatio: _videoPlayerController!.value.aspectRatio,
        showControlsOnInitialize: true,
        fullScreenByDefault: false,
        allowFullScreen: true,
        allowPlaybackSpeedChanging: true,
        materialProgressColors: ChewieProgressColors(
          playedColor: Colors.orange,
          handleColor: Colors.orange,
          backgroundColor: Colors.grey,
          bufferedColor: Colors.white70,
        ),
        additionalOptions: (context) {
          return [
            OptionItem(
              onTap: (context) => _showQualityPicker(context),
              iconData: Icons.hd,
              title: 'Quality',
              subtitle: _currentFormat?.note ?? 'Auto',
            ),
          ];
        },
        placeholder: Container(color: Colors.black),
        autoInitialize: true,
      );
    }

    setState(() => _isLoading = false);
  }

  void _switchQuality(AppVideoFormat format) async {
    if (_currentFormat == format) return;

    // Determine if we should seek to current position (don't seek for 51cg1 sources)
    final bool shouldSeek = !widget.video.site.contains('51cg1');
    Duration currentPosition = Duration.zero;
    
    if (shouldSeek) {
      if (_isWindows) {
        currentPosition = _player!.state.position;
      } else if (_videoPlayerController != null) {
        currentPosition = _videoPlayerController!.value.position;
      }
    }

    // First close the picker bottom sheet if it's open
    Navigator.of(context, rootNavigator: true).pop();
    
    setState(() {
      _currentFormat = format;
      _isLoading = true;
    });

    await _initializePlayer(format.url, format.headers);

    // Seek to saved position if allowed
    if (shouldSeek) {
      if (_isWindows) {
        await _player!.seek(currentPosition);
      } else if (_videoPlayerController != null) {
        await _videoPlayerController!.seekTo(currentPosition);
        await _videoPlayerController!.play();
      }
    }
  }

  void _showQualityPicker(BuildContext context) {
    // We need to pop the Chewie settings menu first if it's on top
    Navigator.of(context).pop();
    
    showModalBottomSheet(
      context: this.context, // Use the page context to ensure correct overlay
      backgroundColor: Colors.black87,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
      ),
      builder: (context) => _buildQualitySelector(),
    );
  }

  Widget _buildQualitySelector() {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 20),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 20, vertical: 10),
            child: Text(
              'Select Quality',
              style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.bold),
            ),
          ),
          Flexible(
            child: ListView(
              shrinkWrap: true,
              children: _videoDetail?.formats.map((format) {
                final isSelected = _currentFormat?.id == format.id;
                return ListTile(
                  leading: Icon(
                    Icons.hd_outlined,
                    color: isSelected ? Colors.orange : Colors.white70,
                  ),
                  title: Text(
                    '${format.note} (${format.height}p)',
                    style: TextStyle(
                      color: isSelected ? Colors.orange : Colors.white,
                      fontWeight: isSelected ? FontWeight.bold : FontWeight.normal,
                    ),
                  ),
                  trailing: isSelected ? const Icon(Icons.check, color: Colors.orange) : null,
                  onTap: () => _switchQuality(format),
                );
              }).toList() ?? [],
            ),
          ),
          const SizedBox(height: 20),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        title: Text(widget.video.title, style: const TextStyle(fontSize: 14)),
        backgroundColor: Colors.black45,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: Center(
        child: _isLoading
            ? const CircularProgressIndicator(color: Colors.orange)
            : _isWindows
                ? mk.Video(controller: _mkController!)
                : _chewieController != null && _chewieController!.videoPlayerController.value.isInitialized
                    ? AspectRatio(
                        aspectRatio: _videoPlayerController!.value.aspectRatio,
                        child: Chewie(controller: _chewieController!),
                      )
                    : const Text('Failed to initialize video player', style: TextStyle(color: Colors.white)),
      ),
    );
  }
}
