import 'package:flutter/material.dart';
import 'dart:convert';
import '../models/video.dart';
import '../services/api_service.dart';
import 'player_page.dart';

class VideoListPage extends StatefulWidget {
  final Site site;
  const VideoListPage({super.key, required this.site});

  @override
  State<VideoListPage> createState() => _VideoListPageState();
}

class _VideoListPageState extends State<VideoListPage> {
  final List<Video> _videos = [];
  bool _isLoading = false;
  int _currentPage = 1;
  final ScrollController _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _loadVideos();
    _scrollController.addListener(_onScroll);
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (_scrollController.position.pixels >= _scrollController.position.maxScrollExtent - 200 &&
        !_isLoading) {
      _loadVideos();
    }
  }

  Future<void> _loadVideos() async {
    if (_isLoading) return;
    setState(() {
      _isLoading = true;
    });

    try {
      final newVideos = await ApiService.getVideos(widget.site.id, _currentPage);
      if (mounted) {
        setState(() {
          _videos.addAll(newVideos);
          _currentPage++;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _isLoading = false;
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error loading videos: $e')),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F0F0F),
      appBar: AppBar(
        title: Text(
          '${widget.site.name.toUpperCase()} CHANNEL',
          style: const TextStyle(fontWeight: FontWeight.bold, letterSpacing: 1.2, fontSize: 18),
        ),
        backgroundColor: Colors.transparent,
        elevation: 0,
      ),
      body: _videos.isEmpty && _isLoading
          ? const Center(child: CircularProgressIndicator(color: Colors.orange))
          : GridView.builder(
              controller: _scrollController,
              padding: const EdgeInsets.fromLTRB(48, 16, 48, 48),
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 3, // 3 columns for better 16:9 visibility on TV
                childAspectRatio: 1.5, // Perfect ratio for thumbnail + title below
                crossAxisSpacing: 32,
                mainAxisSpacing: 32,
              ),
              itemCount: _videos.length + (_isLoading ? 3 : 0),
              itemBuilder: (context, index) {
                if (index >= _videos.length) {
                  return const _VideoCardSkeleton();
                }
                final video = _videos[index];
                return _VideoTVCard(
                  video: video,
                  onTap: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (context) => PlayerPage(video: video),
                      ),
                    );
                  },
                );
              },
            ),
    );
  }
}

class _VideoTVCard extends StatefulWidget {
  final Video video;
  final VoidCallback onTap;

  const _VideoTVCard({required this.video, required this.onTap});

  @override
  State<_VideoTVCard> createState() => _VideoTVCardState();
}

class _VideoTVCardState extends State<_VideoTVCard> {
  bool _isFocused = false;

  Widget _buildThumbnail(String url) {
    if (url.startsWith('data:image')) {
      try {
        final base64String = url.split(',').last;
        return Image.memory(
          base64Decode(base64String),
          fit: BoxFit.cover,
        );
      } catch (e) {
        return Container(color: Colors.grey[900], child: const Icon(Icons.broken_image, color: Colors.white24));
      }
    }
    return Image.network(
      url,
      fit: BoxFit.cover,
      errorBuilder: (context, error, stackTrace) =>
          Container(color: Colors.grey[900], child: const Icon(Icons.movie, color: Colors.white24, size: 48)),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Focus(
      onFocusChange: (focused) => setState(() => _isFocused = focused),
      child: GestureDetector(
        onTap: widget.onTap,
        child: AnimatedScale(
          scale: _isFocused ? 1.08 : 1.0,
          duration: const Duration(milliseconds: 250),
          curve: Curves.easeOutBack,
          child: Container(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: _isFocused ? Colors.orangeAccent : Colors.white.withOpacity(0.05),
                width: _isFocused ? 4 : 1,
              ),
              boxShadow: _isFocused
                  ? [
                      BoxShadow(
                        color: Colors.black.withOpacity(0.8),
                        blurRadius: 25,
                        spreadRadius: 5,
                      ),
                      BoxShadow(
                        color: Colors.orange.withOpacity(0.2),
                        blurRadius: 15,
                        spreadRadius: 0,
                      )
                    ]
                  : [],
            ),
            clipBehavior: Clip.antiAlias,
            child: Stack(
              fit: StackFit.expand,
              children: [
                // Thumbnail
                _buildThumbnail(widget.video.thumbnail),
                // Gradient Overlay
                Positioned.fill(
                  child: Container(
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.topCenter,
                        end: Alignment.bottomCenter,
                        colors: [
                          Colors.transparent,
                          Colors.black.withOpacity(_isFocused ? 0.9 : 0.7),
                        ],
                        stops: const [0.4, 1.0],
                      ),
                    ),
                  ),
                ),
                // Metadata (Title and duration)
                Positioned(
                  bottom: 0,
                  left: 0,
                  right: 0,
                  child: Padding(
                    padding: const EdgeInsets.all(16.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Text(
                          widget.video.title,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(
                            fontWeight: FontWeight.bold,
                            fontSize: 18,
                            color: _isFocused ? Colors.white : Colors.white.withOpacity(0.9),
                            shadows: const [Shadow(color: Colors.black, blurRadius: 4, offset: Offset(1, 1))],
                          ),
                        ),
                        const SizedBox(height: 4),
                        Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                              decoration: BoxDecoration(
                                color: Colors.orange,
                                borderRadius: BorderRadius.circular(4),
                              ),
                              child: Text(
                                widget.video.duration,
                                style: const TextStyle(color: Colors.black, fontSize: 12, fontWeight: FontWeight.w900),
                              ),
                            ),
                            const SizedBox(width: 8),
                            Text(
                              widget.video.site.toUpperCase(),
                              style: TextStyle(color: Colors.white.withOpacity(0.6), fontSize: 12, fontWeight: FontWeight.bold),
                            ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),
                // Play icon overlay when focused
                if (_isFocused)
                  Center(
                    child: Container(
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: Colors.black.withOpacity(0.4),
                      ),
                      padding: const EdgeInsets.all(12),
                      child: const Icon(Icons.play_arrow_rounded, color: Colors.white, size: 48),
                    ),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _VideoCardSkeleton extends StatelessWidget {
  const _VideoCardSkeleton();

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.grey[900],
        borderRadius: BorderRadius.circular(12),
      ),
      child: const Center(
        child: SizedBox(
          width: 30,
          height: 30,
          child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white24),
        ),
      ),
    );
  }
}
