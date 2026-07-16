#!/usr/bin/env perl
# Strip forward-looking episode teasers; output past-ref episode numbers.
use strict;
use warnings;
use utf8;

binmode STDOUT, ':utf8';
binmode STDERR, ':utf8';

my $file = $ARGV[0] or die "usage: clean-episode-refs.pl FILE\n";

open my $fh, '<:utf8', $file or die $!;
local $/;
my $doc = <$fh>;
close $fh;

my ($current) = $doc =~ /^# .*?\((\d+)화\)/;
die "no episode number in $file\n" unless defined $current;
$current += 0;

my ($head, $tail) = split(/## 관련 회차/s, $doc, 2);
$tail //= '';

my ($h1, $rest) = $head =~ /^(.+?\n)(.*)/s;
$h1 //= $head;
$rest //= '';

# --- cleanup (H1 제외) ---
$rest =~ s/\n+다음 \d{1,2}화에서는[^\n]*(?:\n(?![\n#]|\d+\. )[^\n]*)*//g;
$rest =~ s/\n+다음 화에서는[^\n]*(?:\n(?![\n#]|\d+\. )[^\n]*)*//g;
$rest =~ s/\n## 다음 화 예고\n.*?(?=\n## |\n---\n|\z)//s;
$rest =~ s/^[ \t]*[^\n]*\d{1,2}화(?:·\d{1,2}화)?에서[^\n]*(?:다루겠|풀겠|넣겠|정리하겠|비교하겠|다룰|예정)[^\n]*\n//mg;

$rest =~ s{
  [^.\n]*\b(\d{1,2})화(?:·\d{1,2}화)?에서[^.\n]*(?:다루겠|풀겠|넣겠|정리하겠|비교하겠|다룰|예정)[^.\n]*\.?\s*
}{
  ($1 + 0) > $current ? '' : $&
}xge;

$rest =~ s{
  \(\s*(\d{1,2})화[^)]*\)
}{
  ($1 + 0) > $current ? '' : $&
}xge;

$rest =~ s/\n---\n\n---\n/\n---\n/g;
$rest =~ s/\n{3,}/\n\n/g;

my $body = $h1 . $rest;

# --- past retrospective refs ---
my %refs;
my $scan = $rest;

sub add_ref {
  my ($n) = @_;
  return unless defined $n;
  $n += 0;
  return if $n < 1 || $n > 50 || $n >= $current;
  $refs{$n} = 1;
}

sub retro_ctx {
  my ($ctx) = @_;
  return 0 if $ctx =~ /다음\s*\d{0,2}$/;
  return 0 if $ctx =~ /\d{1,2}화에서[^.]{0,40}(?:다루겠|풀겠|넣겠|정리하겠|비교하겠|다룰|예정)/;
  return 1 if $ctx =~ /화에서\s*(?:말했|봤|정리|다뤘|적었|이어|살짝|강조|다룬|말한)/;
  return 1 if $ctx =~ /화·\d{1,2}화에서/;
  return 1 if $ctx =~ /\(\d{1,2}화\)/;
  return 1 if $ctx =~ /시리즈\s*\d{1,2}화에서\s*다뤘/;
  return 0;
}

while ($scan =~ /(?<![0-9])(\d{1,2})화/g) {
  my $n   = $1 + 0;
  my $pos = pos($scan) - length($1) - 1;
  my $start = $pos > 70 ? $pos - 70 : 0;
  my $ctx = substr($scan, $start, 140);
  add_ref($n) if $n < $current && retro_ctx($ctx);
}

while ($scan =~ /(?<![0-9])(\d{1,2})화·(\d{1,2})화에서\s*(?:말|강조|정리|다룬)/g) {
  add_ref($1);
  add_ref($2);
}

while ($scan =~ /(\d{1,2})~(\d{1,2})화에서\s*다룬/g) {
  my ($a, $b) = ($1 + 0, $2 + 0);
  add_ref($_) for grep { $_ < $current } ($a .. $b);
}

$doc = $body;
if ($tail ne '') {
  $doc .= '## 관련 회차' . $tail;
}

open $fh, '>:utf8', $file or die $!;
print $fh $doc;
close $fh;

print join("\n", sort { $a <=> $b } keys %refs);
